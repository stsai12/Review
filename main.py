# main.py
import os
import json
# from serpapi import GoogleSearch # No longer needed
import pandas as pd
# We will import from config.py (though it's less critical now)

def get_user_input():
    """Prompts the user for necessary input parameters."""
    params = {}

    print("Welcome to the Research Article Pipeline (JSON Input Mode)!")
    print("Please provide the following information:")

    # Input JSON file path
    json_file_path = input("Enter the path to your input JSON file (default: input_articles.json in project root): ").strip()
    if not json_file_path:
        json_file_path = "input_articles.json"
    params['json_file_path'] = json_file_path

    # Minimum Publication Year (for filtering data from JSON)
    while True:
        try:
            year_str = input("Enter the minimum publication year for filtering articles from JSON (e.g., 2010, press Enter for no filter): ").strip()
            if not year_str: # Default to no year filter if empty
                params['min_publication_year'] = None
                print("No minimum publication year filter will be applied.")
                break
            year = int(year_str)
            if year > 1000 and year < 2100: # Basic validation
                params['min_publication_year'] = year
                break
            else:
                print("Please enter a valid year (e.g., 2010).")
        except ValueError:
            print("Invalid input. Please enter a number for the year.")

    # Minimum Impact Factor (for filtering data from JSON)
    while True:
        try:
            if_str = input("Enter the minimum acceptable impact factor for filtering (e.g., 2.0, press Enter to skip/default to 0.0): ").strip()
            if not if_str:
                params['min_impact_factor'] = 0.0 # Default to 0.0 if skipped
                print("Minimum impact factor filter will not be strictly applied or defaulted to 0.0.")
                break
            impact_factor = float(if_str)
            if impact_factor >= 0.0:
                params['min_impact_factor'] = impact_factor
                break
            else:
                print("Impact factor cannot be negative.")
        except ValueError:
            print("Invalid input. Please enter a number for the impact factor.")

    return params

def load_articles_from_json(json_filepath):
    """
    Loads articles from a local JSON file (expected SerpAPI full response format).
    Parses article data and returns a pandas DataFrame.
    """
    print(f"Attempting to load articles from: {json_filepath}")
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            raw_json_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at '{json_filepath}'.")
        return pd.DataFrame()
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{json_filepath}'. Check file format.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred while reading '{json_filepath}': {e}")
        return pd.DataFrame()

    if "organic_results" not in raw_json_data or not isinstance(raw_json_data["organic_results"], list):
        print("Error: JSON file does not contain 'organic_results' list or it's not a list.")
        if "error" in raw_json_data:
             print(f"JSON contains an error message: {raw_json_data['error']}")
        return pd.DataFrame()

    articles_list = raw_json_data["organic_results"]
    if not articles_list:
        print("No articles found in 'organic_results'.")
        return pd.DataFrame()

    print(f"Found {len(articles_list)} articles in 'organic_results'. Parsing them...")
    all_articles_data = []

    for item in articles_list:
        title = item.get("title")
        link = item.get("link")
        doi = item.get("publication_info", {}).get("doi")
        snippet = item.get("snippet")
        citation_count = item.get("inline_links", {}).get("cited_by", {}).get("total")

        publication_summary = item.get("publication_info", {}).get("summary", "")

        authors_str = "N/A"
        year_str = "N/A"
        journal_str = "N/A"

        parts = publication_summary.split(" - ")
        if len(parts) > 0:
            authors_str = parts[0].strip()

        if len(parts) > 1:
            remaining_summary = " - ".join(parts[1:])
            year_match = pd.Series(remaining_summary).str.extract(r'(\b(?:19|20)\d{2}\b)')

            if not year_match.empty and year_match.iloc[0,0] is not None:
                year_str = year_match.iloc[0,0]
                journal_candidate = remaining_summary.replace(year_str, "").strip(" ,.-")

                if year_str in parts[-1]: # Year was in the last part of original split
                    if len(parts) > 2:
                        journal_str = parts[-2].strip(" ,.")
                    elif journal_candidate: # Authors - Year-containing-part (Journal might be mixed with year)
                         journal_str = journal_candidate
                    else: # Only Authors and Year string found.
                        journal_str = "N/A"
                else:
                    journal_str = journal_candidate if journal_candidate else "N/A"
            else:
                if len(parts) > 1:
                    journal_str = " - ".join(parts[1:]).strip(" ,.")
                else:
                    journal_str = "N/A"
        else: # Only one part in summary, likely just authors
            journal_str = "N/A"
            year_str = "N/A"


        article_data = {
            "Title": title,
            "Authors": authors_str,
            "Abstract_Snippet": snippet,
            "Year": year_str,
            "Journal_Name": journal_str,
            "DOI": doi,
            "Source_Link": link,
            "Citation_Count": citation_count if citation_count is not None else 0
        }
        all_articles_data.append(article_data)

    if not all_articles_data:
        print("No article data could be parsed successfully.")
        return pd.DataFrame()

    df = pd.DataFrame(all_articles_data)

    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').fillna(0).astype(int)
    df['Citation_Count'] = pd.to_numeric(df['Citation_Count'], errors='coerce').fillna(0).astype(int)

    print(f"Successfully parsed {len(df)} articles into a DataFrame.")
    return df

def filter_articles_basic(df, params):
    """
    Performs initial basic filtering on the retrieved articles.
    - Filters by minimum publication year.
    - Filters out common non-research/non-peer-reviewed keywords in titles.
    """
    if df.empty:
        print("Input DataFrame for basic filtering is empty.")
        return df

    original_count = len(df)
    current_df = df.copy()

    min_year = params.get('min_publication_year')
    if min_year is not None and min_year > 0:
        current_df = current_df[current_df['Year'] >= min_year]
        print(f"Filtering by year: {original_count - len(current_df)} articles removed (older than {min_year} or year parse error).")
        if current_df.empty:
            print("No articles remaining after year filter.")
            return current_df

    exclusion_keywords = [
        "[CITATION]", "[BOOK]", "[PDF]", "Review", "Editorial", "Commentary",
        "Conference", "Proceedings", "Abstracts", "Thesis", "Dissertation",
        "Erratum", "Corrigendum", "Letter to the Editor", "Book review"
    ]
    pattern = '|'.join(exclusion_keywords)
    current_df['Title'] = current_df['Title'].astype(str)
    rows_to_drop = current_df['Title'].str.contains(pattern, case=False, na=False)
    num_dropped_by_keyword = rows_to_drop.sum()

    if num_dropped_by_keyword > 0:
        current_df = current_df[~rows_to_drop]
        print(f"Filtering by title keywords: {num_dropped_by_keyword} articles removed.")

    if current_df.empty:
        print("No articles remaining after title keyword filter.")
        return current_df

    print(f"Basic filtering complete. Total articles removed: {original_count - len(current_df)}")
    return current_df

def enrich_article_metadata(df):
    """
    Placeholder for enriching article metadata using CrossRef/Unpaywall.
    Currently adds placeholder columns for future data.
    """
    if df.empty:
        print("Input DataFrame for enrichment is empty.")
        return df

    print("This is a placeholder for metadata enrichment using CrossRef/Unpaywall.")
    placeholder_cols = {
        "Full_Citation": "N/A", "OA_Status": "Unknown", "PDF_Link": "N/A",
        "Publisher": "N/A", "Journal_ISSN": "N/A"
    }
    for col, default_value in placeholder_cols.items():
        if col not in df.columns:
            df[col] = default_value
    print(f"Added/ensured placeholder columns: {list(placeholder_cols.keys())}")
    return df

def load_impact_factors(filepath="journal_impact_factors.csv"):
    """Loads journal impact factors from a CSV file."""
    try:
        if os.path.exists(filepath):
            df_if = pd.read_csv(filepath)
            print(f"Successfully loaded impact factor data from {filepath}.")
            required_cols = ['Journal_Title', 'Impact_Factor']
            if not all(col in df_if.columns for col in required_cols):
                print(f"Impact factor CSV missing required columns: {required_cols}. Skipping IF filtering.")
                return pd.DataFrame()
            df_if['Impact_Factor'] = pd.to_numeric(df_if['Impact_Factor'], errors='coerce')
            df_if = df_if.dropna(subset=['Impact_Factor'])
            return df_if
        else:
            print(f"Impact factor file '{filepath}' not found. Skipping impact factor filtering.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error loading impact factor file '{filepath}': {e}. Skipping impact factor filtering.")
        return pd.DataFrame()

def filter_articles_advanced(df, params, impact_factors_df):
    """ Performs advanced filtering: by impact factor and refined article type. """
    if df.empty:
        print("Input DataFrame for advanced filtering is empty.")
        return df

    original_count = len(df)
    current_df = df.copy()

    min_impact_factor = params.get('min_impact_factor', 0.0)
    if min_impact_factor > 0.0 and impact_factors_df is not None and not impact_factors_df.empty:
        print(f"Filtering by minimum impact factor: {min_impact_factor}")
        if 'Impact_Factor' not in current_df.columns:
            current_df['Impact_Factor'] = pd.NA
        if 'ISSN' not in impact_factors_df.columns:
             impact_factors_df['ISSN'] = pd.NA # Ensure column exists for matching logic

        for index, row in current_df.iterrows():
            # Ensure journal_name is a string and handle potential None from .get()
            journal_name_val = row.get('Journal_Name')
            journal_name = str(journal_name_val).strip().lower() if pd.notna(journal_name_val) else ""

            journal_issn_val = row.get('Journal_ISSN')
            journal_issn = str(journal_issn_val).strip().lower() if pd.notna(journal_issn_val) else ""

            match_found = False
            # Try matching by ISSN if available and valid
            if journal_issn and 'ISSN' in impact_factors_df.columns and journal_issn != 'n/a':
                # Ensure ISSN in impact_factors_df is also treated as string for comparison
                if_match = impact_factors_df[impact_factors_df['ISSN'].astype(str).str.strip().str.lower() == journal_issn]
                if not if_match.empty:
                    current_df.loc[index, 'Impact_Factor'] = if_match['Impact_Factor'].iloc[0]
                    match_found = True

            # Try matching by Journal Name if no ISSN match or ISSN not available/valid
            if not match_found and journal_name and journal_name != 'n/a':
                if_match = impact_factors_df[impact_factors_df['Journal_Title'].astype(str).str.strip().str.lower() == journal_name]
                if not if_match.empty:
                    current_df.loc[index, 'Impact_Factor'] = if_match['Impact_Factor'].iloc[0]

        current_df['Impact_Factor'] = pd.to_numeric(current_df['Impact_Factor'], errors='coerce')
        initial_len = len(current_df)
        current_df = current_df[(current_df['Impact_Factor'] >= min_impact_factor) | (current_df['Impact_Factor'].isna())]
        articles_dropped_if = initial_len - len(current_df)
        if articles_dropped_if > 0:
            print(f"Impact Factor Filter: Removed {articles_dropped_if} articles with IF < {min_impact_factor}.")
        if current_df.empty:
            print("No articles remaining after impact factor filter.")
            return current_df
    elif min_impact_factor > 0.0:
        print("Minimum impact factor set, but no impact factor data. Skipping IF filter.")

    exclusion_keywords_advanced = [
        "Review Article", "Systematic Review", "Meta-Analysis", "Editorial", "Commentary",
        "Opinion", "Perspective", "Conference Paper", "Conference Proceedings",
        "Meeting Abstract", "Poster Abstract", "Thesis", "Dissertation", "Student Project",
        "Erratum", "Corrigendum", "Retraction", "Letter to Editor", "Book Review",
        "Preprint", "Working Paper", "Rapid Communication", "Short Communication",
        "Case Report", "Case Study", "\[CITATION]", "\[BOOK]", "\[PDF]"
    ]
    pattern_advanced = '|'.join(exclusion_keywords_advanced)
    current_df['Title'] = current_df['Title'].astype(str)
    rows_to_drop_advanced = current_df['Title'].str.contains(pattern_advanced, case=False, na=False)
    num_dropped_by_keyword_advanced = rows_to_drop_advanced.sum()

    if num_dropped_by_keyword_advanced > 0:
        current_df = current_df[~rows_to_drop_advanced]
        print(f"Advanced Title Keyword Filter: Removed {num_dropped_by_keyword_advanced} additional articles.")

    if current_df.empty:
        print("No articles remaining after advanced type filter.")
        return current_df

    print(f"Advanced filtering complete. Total articles removed in this step: {original_count - len(current_df)}")
    return current_df

def group_articles_into_themes_placeholder(df):
    """ Placeholder for grouping articles into themes. """
    if df.empty: return df
    print("Placeholder: Article grouping using topic modeling.")
    if 'Theme' not in df.columns: df['Theme'] = "General"
    else: df['Theme'] = df['Theme'].fillna("General")
    print("Placeholder 'Theme' column added/updated.")
    return df

def generate_review_article_placeholder(df, user_params):
    """ Placeholder for generating a review article using an LLM. """
    if df.empty: return ""
    print("Placeholder: LLM-based review article generation.")

    review_topic_title = user_params.get('json_file_path', 'the loaded data')
    references = [f"- {row.get('Authors', 'N/A')} ({row.get('Year', 'N/A')}). {row.get('Title', 'N/A')}. {row.get('Journal_Name', 'N/A')}."
                  for _, row in df.sort_values(by=['Authors', 'Year', 'Title']).iterrows()]

    md_content = f"# Review Article based on: {review_topic_title}\n\n"
    md_content += "## Abstract\n\n[LLM-generated abstract...]\n\n"
    md_content += "## 1. Introduction\n\n[LLM-generated introduction...]\n\n"

    themes = df['Theme'].unique()
    section_number = 2
    for theme_name in themes:
        md_content += f"## {section_number}. Thematic Section: {theme_name}\n\n[LLM-synthesized content for '{theme_name}'...]\n\n"
        md_content += f"**Key articles for this theme might include:**\n"
        theme_articles = df[df['Theme'] == theme_name].head(3)
        for _, article_row in theme_articles.iterrows():
             md_content += f"- *{article_row.get('Title', 'N/A')}* ({article_row.get('Authors', 'N/A')}, {article_row.get('Year', 'N/A')})\n"
        md_content += "\n"
        section_number += 1

    md_content += f"## {section_number}. Discussion and Future Directions\n\n[LLM-generated discussion...]\n\n"
    md_content += f"## {section_number + 1}. Conclusion\n\n[LLM-generated conclusion...]\n\n"
    md_content += f"## {section_number + 2}. References\n\n" + ("\n".join(references) if references else "N/A") + "\n"

    print("Generated placeholder Markdown for the review article.")
    return md_content

def ai_content_detection_conceptual_step():
    """ Outlines the conceptual process for AI content detection. """
    print("\n--- AI Content Detection and Refinement (Conceptual Workflow) ---")
    print("1. Input: LLM-generated review article segments.")
    print("2. API Call: Send text to AI detection service (e.g., Originality.ai).")
    print("3. Decision & Refinement: If score > threshold (e.g., 10%), flag for rewrite (automated/manual).")
    print("4. Iteration: Repeat until segments pass or max attempts reached.")
    print("5. Output: Refined review article meeting AI detection criteria.")
    print("--- End of Conceptual Workflow ---\n")

def generate_final_outputs(df, user_params):
    """ Generates and saves the final outputs. """
    print("Generating final output files...")
    try:
        df.to_csv("outputs/final_articles_for_review.csv", index=False)
        print("Final articles saved to outputs/final_articles_for_review.csv")
        df.to_json("outputs/final_articles_for_review.json", orient="records", indent=4)
        print("Final articles saved to outputs/final_articles_for_review.json")
    except Exception as e: print(f"Error saving final articles list: {e}")

    summary_table_md = "## Article Summary Table\n\n"
    if not df.empty:
        cols = ['Title', 'Authors', 'Year', 'Journal_Name', 'Theme', 'Citation_Count', 'DOI', 'Impact_Factor']
        summary_df = df[[col for col in cols if col in df.columns]].copy() # Ensure only existing cols selected
        summary_df.fillna('N/A', inplace=True)
        summary_table_md += summary_df.to_markdown(index=False)
    else: summary_table_md += "No articles processed.\n"

    try:
        with open("outputs/article_summary_table.md", "w", encoding="utf-8") as f: f.write(summary_table_md)
        print("Article summary table saved to outputs/article_summary_table.md")
    except IOError as e: print(f"Error saving article summary table: {e}")
    print("Final output generation complete.")

def main():
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        print("Created 'outputs' directory.")

    user_params = get_user_input()

    try:
        with open("outputs/run_parameters.json", "w") as f: json.dump(user_params, f, indent=4)
        print(f"User parameters saved to outputs/run_parameters.json")
    except IOError as e: print(f"Error saving parameters: {e}")

    print("\nCollected Parameters:")
    for key, value in user_params.items(): print(f"- {key.replace('_', ' ').title()}: {value}")

    print("\nStarting literature loading from JSON...")
    articles_df = load_articles_from_json(user_params['json_file_path'])

    if articles_df is not None and not articles_df.empty:
        print(f"Successfully loaded and parsed {len(articles_df)} articles from {user_params['json_file_path']}.")
        try:
            articles_df.to_json("outputs/loaded_articles_from_json.json", orient="records", indent=4) # Changed filename
            print(f"Parsed articles from JSON saved to outputs/loaded_articles_from_json.json")
        except Exception as e:
            print(f"Error saving loaded articles: {e}")
    else:
        print(f"Literature loading from {user_params['json_file_path']} failed or no articles found/parsed.")
        articles_df = pd.DataFrame() # Ensure df is empty for subsequent steps

    # Basic Filtering
    filtered_df_basic = filter_articles_basic(articles_df.copy(), user_params) if not articles_df.empty else pd.DataFrame()
    if not articles_df.empty and not filtered_df_basic.empty :
        print(f"After basic filtering, {len(filtered_df_basic)} articles remain.")
        try:
            filtered_df_basic.to_json("outputs/articles_filtered_basic.json", orient="records", indent=4)
            filtered_df_basic.to_csv("outputs/articles_filtered_basic.csv", index=False)
            print(f"Basic filtered articles saved.")
        except Exception as e: print(f"Error saving basic filtered articles: {e}")
    elif not articles_df.empty and filtered_df_basic.empty:
        print("Basic filtering resulted in an empty dataset.")
    # else: (articles_df was empty to begin with) handled by initial check


    # Metadata Enrichment (Placeholder)
    enriched_df = enrich_article_metadata(filtered_df_basic.copy()) if not filtered_df_basic.empty else pd.DataFrame()
    # ... (logging for enrichment can be added if desired)

    # Advanced Filtering
    current_df_for_advanced = enriched_df if not enriched_df.empty else filtered_df_basic # Use whatever is available
    filtered_df_advanced = pd.DataFrame()
    if not current_df_for_advanced.empty:
        print("\nStarting advanced article filtering...")
        impact_factors_df = load_impact_factors()
        filtered_df_advanced = filter_articles_advanced(current_df_for_advanced.copy(), user_params, impact_factors_df)
        if not filtered_df_advanced.empty:
            print(f"After advanced filtering, {len(filtered_df_advanced)} articles remain.")
            try:
                filtered_df_advanced.to_json("outputs/articles_filtered_advanced.json", orient="records", indent=4)
                filtered_df_advanced.to_csv("outputs/articles_filtered_advanced.csv", index=False)
                print("Advanced filtered articles saved.")
            except Exception as e: print(f"Error saving advanced filtered articles: {e}")
        else: print("Advanced filtering resulted in an empty dataset.")
    # else: (no data for advanced filtering)


    # Article Grouping (Placeholder)
    current_df_for_grouping = filtered_df_advanced if not filtered_df_advanced.empty else (enriched_df if not enriched_df.empty else filtered_df_basic)
    themed_df = pd.DataFrame()
    if not current_df_for_grouping.empty:
        themed_df = group_articles_into_themes_placeholder(current_df_for_grouping.copy())
        if not themed_df.empty:
            try:
                themed_df.to_json("outputs/articles_themed_placeholder.json", orient="records", indent=4)
                themed_df.to_csv("outputs/articles_themed_placeholder.csv", index=False)
                print("Themed article data (placeholder) saved.")
            except Exception as e: print(f"Error saving themed articles: {e}")
    # else: (no data for theming)


    # Review Article Generation (Placeholder)
    current_df_for_generation = themed_df if not themed_df.empty else pd.DataFrame() # Use last valid df
    if not current_df_for_generation.empty:
        review_content_md = generate_review_article_placeholder(current_df_for_generation, user_params)
        if review_content_md:
            try:
                with open("outputs/generated_review_article_placeholder.md", "w", encoding="utf-8") as f: f.write(review_content_md)
                print("Placeholder review article saved.")
            except IOError as e: print(f"Error saving placeholder review article: {e}")
    # else: (no data for generation)

    # AI Content Detection (Conceptual)
    ai_content_detection_conceptual_step() # This just prints info

    # Final Output Generation
    final_output_source_df = themed_df if not themed_df.empty else \
                             (filtered_df_advanced if not filtered_df_advanced.empty else \
                              (enriched_df if not enriched_df.empty else \
                               (filtered_df_basic if not filtered_df_basic.empty else articles_df)))

    if not final_output_source_df.empty:
        print("\nStarting final output generation...")
        generate_final_outputs(final_output_source_df, user_params)
    else:
        print("\nSkipping final output generation as no data was successfully processed through the pipeline.")

    print("\nPipeline execution finished.")
    print(f"All outputs can be found in the '{os.getcwd()}/outputs' directory.")

if __name__ == "__main__":
    main()
