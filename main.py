# main.py
import os
import json
from serpapi import GoogleSearch # Corrected import
import pandas as pd
# We will import from config.py, but it's better to handle API keys via environment variables
# For now, we'll show how to potentially load it, but also prompt if not found.

def get_user_input():
    """Prompts the user for necessary input parameters."""
    params = {}

    print("Welcome to the Research Article Pipeline!")
    print("Please provide the following information:")

    # SerpAPI Key
    api_key = os.getenv('SERPAPI_API_KEY')
    if not api_key:
        api_key = input("Enter your SerpAPI API key: ").strip()
    if not api_key:
        print("SerpAPI key is required to proceed.")
        exit()
    params['serpapi_api_key'] = api_key

    # Search Keyword
    keyword = input("Enter the keyword or topic for search (e.g., “lipid oxidation in oil-in-water emulsions”): ").strip()
    if not keyword:
        print("Search keyword is required.")
        exit()
    params['search_keyword'] = keyword

    # Minimum Publication Year
    while True:
        try:
            year_str = input("Enter the minimum publication year (e.g., 2010, press Enter for no filter): ").strip()
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

    # Minimum Impact Factor
    while True:
        try:
            if_str = input("Enter the minimum acceptable impact factor (e.g., 2.0, press Enter to skip/default to 0.0): ").strip()
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

    # Preferred Number of Articles
    while True:
        try:
            num_str = input("Enter the preferred number of articles to fetch (e.g., 100, press Enter to default to 50): ").strip()
            if not num_str:
                 params['preferred_article_count'] = 50 # Default to 50
                 print(f"Defaulting to {params['preferred_article_count']} articles.")
                 break
            num_articles = int(num_str)
            if num_articles > 0:
                params['preferred_article_count'] = num_articles
                break
            else:
                print("Please enter a positive number for the article count.")
        except ValueError:
            print("Invalid input. Please enter a number for the article count.")

    return params

def main():
    # Create outputs directory if it doesn't exist
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        print("Created 'outputs' directory.")

    user_params = get_user_input()

    # Store parameters for reproducibility
    try:
        with open("outputs/run_parameters.json", "w") as f:
            json.dump(user_params, f, indent=4)
        print(f"User parameters saved to outputs/run_parameters.json")
    except IOError as e:
        print(f"Error saving parameters: {e}")

    print("\nCollected Parameters:")
    for key, value in user_params.items():
        print(f"- {key.replace('_', ' ').title()}: {value}")

    print("\nPipeline execution would start here using these parameters...")

    print("\nStarting literature retrieval...")
    articles_df = retrieve_articles(user_params)
    if articles_df is not None and not articles_df.empty:
        print(f"Successfully retrieved and processed {len(articles_df)} articles.")
        print(f"Raw article data saved to outputs/retrieved_articles_raw.json")
        # print(articles_df.head()) # For debugging

        print("\nStarting basic article filtering...")
        filtered_df_basic = filter_articles_basic(articles_df, user_params)
        if filtered_df_basic is not None:
            print(f"After basic filtering, {len(filtered_df_basic)} articles remain.")
            try:
                # Save to JSON
                filtered_df_basic.to_json("outputs/articles_filtered_basic.json", orient="records", indent=4)
                print(f"Basic filtered articles saved to outputs/articles_filtered_basic.json")
                # Save to CSV for easier inspection if needed
                filtered_df_basic.to_csv("outputs/articles_filtered_basic.csv", index=False)
                print(f"Basic filtered articles saved to outputs/articles_filtered_basic.csv")

            except Exception as e:
                print(f"Error saving basic filtered articles: {e}")
        else:
            print("Basic filtering resulted in an empty dataset or an error occurred.")
            # Even if filtering failed, ensure filtered_df_basic is defined for next steps
            filtered_df_basic = pd.DataFrame()

    else:
        print("Literature retrieval failed or no articles found. Skipping filtering.")
        filtered_df_basic = pd.DataFrame() # Ensure it's defined

    # Metadata Enrichment Step (Placeholder)
    print("\nStarting metadata enrichment (placeholder)...")
    enriched_df = enrich_article_metadata(filtered_df_basic.copy() if not filtered_df_basic.empty else pd.DataFrame())
    if enriched_df is not None and not enriched_df.empty:
        print(f"Metadata enrichment placeholder step complete. DataFrame now has {len(enriched_df.columns)} columns.")
        # Optionally save this intermediate step if actual enrichment were done
        # enriched_df.to_json("outputs/articles_enriched.json", orient="records", indent=4)
        # print("Enriched article data (placeholder) saved.")
    elif filtered_df_basic.empty:
        print("Skipping enrichment as there's no data from previous step.")
    else:
        print("Metadata enrichment (placeholder) did not modify the DataFrame or resulted in an empty set.")


    # print("\nStarting advanced article filtering...")
    current_df_for_advanced_filtering = enriched_df if enriched_df is not None and not enriched_df.empty else filtered_df_basic

    if current_df_for_advanced_filtering is not None and not current_df_for_advanced_filtering.empty:
        print("\nStarting advanced article filtering...")
        impact_factors_df = load_impact_factors() # Tries to load journal_impact_factors.csv

        filtered_df_advanced = filter_articles_advanced(
            current_df_for_advanced_filtering.copy(),
            user_params,
            impact_factors_df
        )

        if filtered_df_advanced is not None:
            print(f"After advanced filtering, {len(filtered_df_advanced)} articles remain.")
            try:
                filtered_df_advanced.to_json("outputs/articles_filtered_advanced.json", orient="records", indent=4)
                print("Advanced filtered articles saved to outputs/articles_filtered_advanced.json")
                filtered_df_advanced.to_csv("outputs/articles_filtered_advanced.csv", index=False)
                print("Advanced filtered articles saved to outputs/articles_filtered_advanced.csv")
            except Exception as e:
                print(f"Error saving advanced filtered articles: {e}")
        else:
            print("Advanced filtering resulted in an empty dataset or an error.")
    elif filtered_df_basic.empty and (enriched_df is None or enriched_df.empty): # Check if there was any data to begin with
         print("Skipping advanced filtering as there is no data from previous steps.")
    # else: # This case implies current_df_for_advanced_filtering was None or empty, already handled by the if condition.
         # print("Advanced filtering skipped as the input DataFrame is empty.")

    # Article Grouping (Topic Modeling - Placeholder)
    current_df_for_grouping = filtered_df_advanced if filtered_df_advanced is not None and not filtered_df_advanced.empty else pd.DataFrame()

    if not current_df_for_grouping.empty:
        print("\nStarting article grouping (placeholder for topic modeling)...")
        themed_df = group_articles_into_themes_placeholder(current_df_for_grouping.copy())
        if themed_df is not None and not themed_df.empty:
            print(f"Article grouping placeholder step complete. DataFrame now has a 'Theme' column.")
            # Optionally save this intermediate step
            themed_df.to_json("outputs/articles_themed_placeholder.json", orient="records", indent=4)
            print("Themed article data (placeholder) saved to outputs/articles_themed_placeholder.json")
            themed_df.to_csv("outputs/articles_themed_placeholder.csv", index=False)
            print("Themed article data (placeholder) saved to outputs/articles_themed_placeholder.csv")
        else:
            print("Article grouping (placeholder) did not modify the DataFrame or resulted in an empty set.")
    else:
        print("Skipping article grouping as there is no data from previous filtering steps.")
        themed_df = pd.DataFrame() # Ensure themed_df is defined for the next step

    # Review Article Generation (LLM - Placeholder)
    current_df_for_generation = themed_df if themed_df is not None and not themed_df.empty else pd.DataFrame()
    if not current_df_for_generation.empty:
        print("\nStarting review article generation (placeholder for LLM interaction)...")
        review_content_md = generate_review_article_placeholder(current_df_for_generation, user_params)
        if review_content_md:
            try:
                with open("outputs/generated_review_article_placeholder.md", "w", encoding="utf-8") as f:
                    f.write(review_content_md)
                print("Placeholder review article saved to outputs/generated_review_article_placeholder.md")
            except IOError as e:
                print(f"Error saving placeholder review article: {e}")
        else:
            print("Placeholder review article generation failed to produce content.")
    else:
        print("Skipping review article generation as there is no themed data available.")

    # AI Content Detection and Refinement (Conceptual)
    print("\nStarting AI Content Detection and Refinement (Conceptual Step)...")
    ai_content_detection_conceptual_step()
    print("AI Content Detection and Refinement conceptual step outlined.")

    # Final Output Generation
    print("\nStarting final output generation...")
    final_output_df = themed_df if themed_df is not None and not themed_df.empty else pd.DataFrame() # Or whatever the last valid df is

    if not final_output_df.empty:
        generate_final_outputs(final_output_df, user_params)
    else:
        print("Skipping final output generation as there is no data from previous steps.")

    print("\nPipeline execution finished.")
    print(f"All outputs can be found in the '{os.getcwd()}/outputs' directory.")


def generate_final_outputs(df, user_params):
    """
    Generates and saves the final outputs of the pipeline.
    - Saves the final list of articles (CSV, JSON).
    - Creates an article summary table (Markdown).
    - Ensures query parameters are saved (already done in main).
    - The main review article (Markdown) is already saved by its generation step.
    """
    print("Generating final output files...")

    # 1. Save the final DataFrame of articles
    try:
        df.to_csv("outputs/final_articles_for_review.csv", index=False)
        print("Final list of articles saved to outputs/final_articles_for_review.csv")
        df.to_json("outputs/final_articles_for_review.json", orient="records", indent=4)
        print("Final list of articles saved to outputs/final_articles_for_review.json")
    except Exception as e:
        print(f"Error saving final articles list: {e}")

    # 2. Generate Article Summary Table (Markdown)
    summary_table_md = "## Article Summary Table\n\n"
    if not df.empty:
        # Selecting key columns for the summary table
        # Adjust columns as needed
        summary_df = df[['Title', 'Authors', 'Year', 'Journal_Name', 'Theme', 'Citation_Count', 'DOI', 'Impact_Factor']].copy()
        summary_df.fillna('N/A', inplace=True) # Replace NaN with N/A for display
        summary_table_md += summary_df.to_markdown(index=False)
    else:
        summary_table_md += "No articles were processed to include in the summary table.\n"

    try:
        with open("outputs/article_summary_table.md", "w", encoding="utf-8") as f:
            f.write(summary_table_md)
        print("Article summary table saved to outputs/article_summary_table.md")
    except IOError as e:
        print(f"Error saving article summary table: {e}")

    # 3. Query parameters are already saved in main() as 'run_parameters.json'
    # 4. Review article (placeholder) is already saved as 'generated_review_article_placeholder.md'

    print("Final output generation complete.")


def ai_content_detection_conceptual_step():
    """
    Outlines the conceptual process for AI content detection and refinement.
    This function is for descriptive purposes only.
    """
    print("--- AI Content Detection and Refinement (Conceptual Workflow) ---")
    print("This step is crucial for ensuring the generated review article meets the low AI detection score requirement (e.g., <10%).")
    print("It would typically involve the following (not implemented in this placeholder script):")
    print("\n1. Input: The generated review article content (e.g., paragraph by paragraph).")
    print("\n2. AI Detection API Call:")
    print("   - For each segment of LLM-generated text:")
    print("     - Send the text to an AI detection service (e.g., Originality.ai, GPTZero, Sapling API).")
    print("     - Receive an AI-generated score.")
    print("\n3. Decision and Refinement:")
    print("   - If the score exceeds the defined threshold (e.g., 10%):")
    print("     - Flag the segment for refinement.")
    print("     - Refinement Strategies:")
    print("       a) Automated Rewrite: Prompt an LLM to rewrite/paraphrase the flagged segment, aiming for a lower AI score while maintaining accuracy and citations. This might be iterative.")
    print("       b) Manual Review: Alert the user to manually review and edit the flagged segment. This is often necessary for quality assurance.")
    print("       c) Hybrid Approach: Attempt automated rewrite, then escalate to manual review if the score remains high.")
    print("\n4. Iteration:")
    print("   - Repeat detection and refinement until all segments pass the threshold or a defined limit (e.g., max rewrite attempts) is reached.")
    print("\n5. Output: The refined review article, ideally with all sections passing the AI detection criteria.")
    print("\nImportant Considerations:")
    print("   - API Keys: Requires API keys for the chosen AI detection service(s).")
    print("   - Cost: API calls for both LLM generation and AI detection can incur costs.")
    print("   - Accuracy: The reliability of AI detection tools can vary.")
    print("   - Scientific Integrity: Refinement must not compromise the scientific accuracy or the proper attribution of cited works.")
    print("--- End of Conceptual Workflow ---")


def generate_review_article_placeholder(df, user_params):
    """
    Placeholder for generating a full-length review article using an LLM.
    Currently generates a Markdown template with placeholders and a basic reference list.
    """
    if df.empty:
        print("Input DataFrame for review generation is empty.")
        return ""

    print("This is a placeholder for LLM-based review article generation.")
    print("Actual implementation would involve prompting an LLM with article data for each theme.")

    keyword = user_params.get('search_keyword', 'the specified topic')

    # Basic APA-ish reference formatting (simplified)
    references = []
    df_sorted_for_ref = df.sort_values(by=['Authors', 'Year', 'Title']).reset_index() # Sort for consistent numbering if used
    for index, row in df_sorted_for_ref.iterrows():
        authors = row.get('Authors', 'N/A')
        year = row.get('Year', 'N/A')
        title = row.get('Title', 'N/A')
        journal = row.get('Journal_Name', 'N/A')
        # For numbered references:
        # references.append(f"{index + 1}. {authors} ({year}). {title}. *{journal}*.")
        # For APA-like list (without italics for journal here for simplicity in MD):
        references.append(f"- {authors} ({year}). {title}. {journal}.")


    # Structure the review
    md_content = f"# Review Article on: {keyword}\n\n"
    md_content += "## Abstract\n\n"
    md_content += "[LLM-generated abstract summarizing the key findings and scope of this review would go here.]\n\n"
    md_content += "## 1. Introduction\n\n"
    md_content += f"[LLM-generated introduction providing background on '{keyword}', stating the review's objectives, and outlining its structure would go here.]\n\n"

    # Generate sections per theme
    # In this placeholder, we only have a "General" theme or whatever is in df['Theme']
    # A real version would loop through unique themes from df['Theme'].unique()

    themes = df['Theme'].unique()
    section_number = 2
    for theme_name in themes:
        md_content += f"## {section_number}. Thematic Section: {theme_name}\n\n"
        md_content += f"[LLM-synthesized content for the theme '{theme_name}' would go here. This would involve summarizing findings, comparing methodologies, and highlighting trends from the articles under this theme, with appropriate citations.]\n\n"

        md_content += f"**Key articles for this theme might include:**\n"
        theme_articles = df[df['Theme'] == theme_name].head(5) # Display a few example articles for the theme
        for _, article_row in theme_articles.iterrows():
            # Example of how one might list articles to be summarized by LLM
            # This would be part of the prompt, not the review text itself usually
            # For the placeholder, we can list some titles:
             md_content += f"- *{article_row.get('Title', 'N/A')}* ({article_row.get('Authors', 'N/A')}, {article_row.get('Year', 'N/A')})\n"
        md_content += "\n"
        section_number += 1

    md_content += f"## {section_number}. Discussion and Future Directions\n\n"
    md_content += "[LLM-generated discussion synthesizing the overall findings across themes, highlighting gaps in the literature, and suggesting future research directions for '{keyword}' would go here.]\n\n"

    section_number += 1
    md_content += f"## {section_number}. Conclusion\n\n"
    md_content += f"[LLM-generated conclusion summarizing the main points of the review on '{keyword}' would go here.]\n\n"

    section_number += 1
    md_content += f"## {section_number}. References\n\n"
    if references:
        md_content += "\n".join(references)
    else:
        md_content += "No articles were processed to generate references.\n"
    md_content += "\n"

    print("Generated placeholder Markdown structure for the review article.")
    return md_content

def group_articles_into_themes_placeholder(df):
    """
    Placeholder for grouping articles into themes using topic modeling.
    Currently adds a placeholder 'Theme' column.
    """
    if df.empty:
        print("Input DataFrame for theming is empty.")
        return df

    print("This is a placeholder for article grouping using topic modeling (e.g., LDA, Sentence-BERT + clustering).")
    print("Actual implementation would involve NLP techniques to analyze titles/abstracts and assign themes.")
    print("For now, a default theme 'General' will be assigned to all articles.")

    if 'Theme' not in df.columns:
        df['Theme'] = "General"
    else: # If 'Theme' column somehow exists, ensure it's populated for consistency if needed
        df['Theme'] = df['Theme'].fillna("General")

    # In a real implementation, this function would:
    # 1. Preprocess text data (titles, abstracts).
    # 2. Apply a topic modeling algorithm (e.g., Gensim for LDA, scikit-learn for NMF, or sentence-transformers for embeddings then clustering).
    # 3. Assign dominant topic(s) or cluster labels to each article in the 'Theme' column.
    # 4. Potentially generate human-readable names for themes.

    print("Placeholder 'Theme' column added/updated.")
    return df

def load_impact_factors(filepath="journal_impact_factors.csv"):
    """Loads journal impact factors from a CSV file."""
    try:
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            print(f"Successfully loaded impact factor data from {filepath}.")
            # Basic validation: check for required columns
            required_cols = ['Journal_Title', 'Impact_Factor']
            if not all(col in df.columns for col in required_cols):
                print(f"Impact factor CSV is missing one of the required columns: {required_cols}. Skipping IF filtering.")
                return pd.DataFrame()
            df['Impact_Factor'] = pd.to_numeric(df['Impact_Factor'], errors='coerce')
            df = df.dropna(subset=['Impact_Factor']) # Remove rows where IF could not be parsed
            return df
        else:
            print(f"Impact factor file '{filepath}' not found. Skipping impact factor filtering.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error loading impact factor file '{filepath}': {e}. Skipping impact factor filtering.")
        return pd.DataFrame()

def filter_articles_advanced(df, params, impact_factors_df):
    """
    Performs advanced filtering: by impact factor and refined article type.
    """
    if df.empty:
        print("Input DataFrame for advanced filtering is empty.")
        return df

    original_count = len(df)
    current_df = df.copy()

    # 1. Impact Factor Filtering
    min_impact_factor = params.get('min_impact_factor', 0.0)
    if min_impact_factor > 0.0 and impact_factors_df is not None and not impact_factors_df.empty:
        print(f"Filtering by minimum impact factor: {min_impact_factor}")

        # Add placeholder for Impact_Factor if not exists
        if 'Impact_Factor' not in current_df.columns:
            current_df['Impact_Factor'] = pd.NA
        if 'ISSN' not in impact_factors_df.columns: # If IF file doesn't have ISSN, matching on title only
            impact_factors_df['ISSN'] = pd.NA

        # Attempt to merge/map. Prioritize ISSN if available in both.
        # This is a simplified matching. Fuzzy matching would be more robust but complex.
        for index, row in current_df.iterrows():
            journal_name = row.get('Journal_Name', '').strip().lower()
            journal_issn = row.get('Journal_ISSN', '').strip() # From placeholder enrichment

            match_found = False
            if pd.notna(journal_issn) and 'ISSN' in impact_factors_df.columns:
                if_match = impact_factors_df[impact_factors_df['ISSN'].astype(str).str.strip().str.lower() == journal_issn.lower()]
                if not if_match.empty:
                    current_df.loc[index, 'Impact_Factor'] = if_match['Impact_Factor'].iloc[0]
                    match_found = True

            if not match_found and journal_name:
                if_match = impact_factors_df[impact_factors_df['Journal_Title'].str.strip().str.lower() == journal_name]
                if not if_match.empty:
                    current_df.loc[index, 'Impact_Factor'] = if_match['Impact_Factor'].iloc[0]
                    match_found = True

            if not match_found:
                # print(f"No impact factor found for journal: {row.get('Journal_Name')}, ISSN: {journal_issn}")
                pass # Keep as NA

        # Now filter
        # Articles with NA impact factor are kept (conservative approach)
        # Convert Impact_Factor column to numeric, coercing errors, before comparison
        current_df['Impact_Factor'] = pd.to_numeric(current_df['Impact_Factor'], errors='coerce')

        # Keep rows where Impact_Factor is >= min_impact_factor OR where Impact_Factor is NA (unknown)
        initial_len = len(current_df)
        current_df = current_df[(current_df['Impact_Factor'] >= min_impact_factor) | (current_df['Impact_Factor'].isna())]
        articles_dropped_if = initial_len - len(current_df)
        if articles_dropped_if > 0:
            print(f"Impact Factor Filter: Removed {articles_dropped_if} articles with IF < {min_impact_factor}.")

        if current_df.empty:
            print("No articles remaining after impact factor filter.")
            return current_df
    elif min_impact_factor > 0.0:
        print("Minimum impact factor set, but no impact factor data loaded. Skipping this filter.")

    # 2. Refined Article Type Filtering (building upon basic or replacing it)
    # This step is largely similar to the basic title keyword filtering but could be expanded.
    # For now, we'll use a slightly more comprehensive list of keywords.
    # If basic filtering already removed these, this won't remove many more.
    # We assume basic filtering was already done. This is an *additional* check or refinement.

    exclusion_keywords_advanced = [
        # Keywords from basic filter (some might be redundant if basic filter ran)
        "\[CITATION]", "\[BOOK]", "\[PDF]", "Review Article", "Systematic Review", "Meta-Analysis", # Be careful with "Review" if some specific reviews are desired
        "Editorial", "Commentary", "Opinion", "Perspective",
        "Conference Paper", "Conference Proceedings", "Meeting Abstract", "Poster Abstract",
        "Thesis", "Dissertation", "Student Project",
        "Erratum", "Corrigendum", "Retraction", "Letter to Editor", "Book Review",
        "Preprint", "Working Paper", # For sources like arXiv, bioRxiv if identifiable
        "Rapid Communication", "Short Communication", # These can be original research but sometimes are less substantial
        "Case Report", "Case Study" # Often not full research articles
    ]
    # A stricter policy might remove "Rapid Communication", "Short Communication", "Case Report"
    # For now, keeping them requires careful consideration of the research domain.
    # Let's refine the list for general scientific review to be a bit more aggressive on non-original research types.

    pattern_advanced = '|'.join(exclusion_keywords_advanced)
    current_df['Title'] = current_df['Title'].astype(str) # Ensure string type

    rows_to_drop_advanced = current_df['Title'].str.contains(pattern_advanced, case=False, na=False)
    num_dropped_by_keyword_advanced = rows_to_drop_advanced.sum()

    if num_dropped_by_keyword_advanced > 0:
        current_df = current_df[~rows_to_drop_advanced]
        print(f"Advanced Title Keyword Filter: Removed {num_dropped_by_keyword_advanced} additional articles.")

    # Additionally, one might filter based on 'Source_Link' for preprint servers if desired.
    # Example:
    # preprint_domains = ['arxiv.org', 'biorxiv.org', 'medrxiv.org']
    # if 'Source_Link' in current_df.columns:
    #    pattern_preprint_link = '|'.join(preprint_domains)
    #    rows_to_drop_preprint = current_df['Source_Link'].str.contains(pattern_preprint_link, case=False, na=False)
    #    num_dropped_preprint = rows_to_drop_preprint.sum()
    #    if num_dropped_preprint > 0:
    #        current_df = current_df[~rows_to_drop_preprint]
    #        print(f"Preprint Filter (Source Link): Removed {num_dropped_preprint} articles from known preprint servers.")

    if current_df.empty:
        print("No articles remaining after advanced type filter.")
        return current_df

    print(f"Advanced filtering complete. Total articles removed in this step: {original_count - len(current_df)}")
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
    print("Actual implementation would involve API calls to fetch full citations, OA status, PDF links, etc.")

    # Add placeholder columns that would be filled by actual enrichment
    placeholder_cols = {
        "Full_Citation": "N/A",
        "OA_Status": "Unknown",
        "PDF_Link": "N/A",
        "Publisher": "N/A",
        "Journal_ISSN": "N/A" # Example: useful for impact factor lookup
    }

    for col, default_value in placeholder_cols.items():
        if col not in df.columns:
            df[col] = default_value

    print(f"Added/ensured placeholder columns: {list(placeholder_cols.keys())}")

    # In a real implementation, you would iterate through rows, use DOIs to query APIs,
    # and fill these columns. For example:
    # for index, row in df.iterrows():
    #     if pd.notna(row['DOI']):
    #         # crossref_data = query_crossref(row['DOI'])
    #         # unpaywall_data = query_unpaywall(row['DOI'])
    #         # df.loc[index, 'Full_Citation'] = ...
    #         # df.loc[index, 'OA_Status'] = ...
    #         # df.loc[index, 'PDF_Link'] = ...
    pass # Placeholder, no actual API calls

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

    # 1. Filter by Minimum Publication Year
    min_year = params.get('min_publication_year')
    if min_year is not None and min_year > 0:
        # Assuming 'Year' is an integer column. Articles with Year 0 (parsing error) will be filtered.
        current_df = current_df[current_df['Year'] >= min_year]
        print(f"Filtering by year: {original_count - len(current_df)} articles removed (older than {min_year} or year parse error).")
        if current_df.empty:
            print("No articles remaining after year filter.")
            return current_df

    # 2. Filter by keywords in title
    # These keywords often indicate non-original research or non-peer-reviewed content.
    # Case-insensitive search.
    exclusion_keywords = [
        "[CITATION]", "[BOOK]", "[PDF]", "Review", "Editorial", "Commentary",
        "Conference", "Proceedings", "Abstracts", "Thesis", "Dissertation",
        "Erratum", "Corrigendum", "Letter to the Editor", "Book review"
    ]

    # Create a regex pattern: \b(keyword1|keyword2|...)\b for whole word matching, case insensitive
    # Or simpler: just check for substring containment if whole word is too restrictive initially
    pattern = '|'.join(exclusion_keywords)

    # Ensure 'Title' column is string type to prevent errors with .str accessor
    current_df['Title'] = current_df['Title'].astype(str)

    # Filter out rows where the title contains any of the exclusion keywords (case-insensitive)
    # `na=False` ensures that if a title is NaN (shouldn't happen with astype(str)), it's not considered a match.
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

def retrieve_articles(params):
    """
    Retrieves articles from Google Scholar using SerpAPI based on user parameters.
    """
    api_key = params['serpapi_api_key']
    query = params['search_keyword']
    min_year = params['min_publication_year']
    num_articles_to_fetch = params['preferred_article_count']

    all_articles_data = []
    current_article_count = 0
    page_num = 0 # SerpAPI uses 'start' parameter, 0 for first page, 10 for second, etc.

    while current_article_count < num_articles_to_fetch:
        query_params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": api_key, # API key is part of the params for GoogleSearch
            "hl": "en",
            "num": 20, # Google Scholar max per page is 20 via SerpAPI's `num` parameter
            "start": page_num * 20, # `start` is the result offset
            "sort_by": "citation_count", # As per user requirement for "top by citation count"
        }
        if min_year:
            query_params["as_ylo"] = str(min_year) # Set minimum year

        print(f"Fetching page {page_num + 1} (articles {current_article_count+1} to {current_article_count + 20})...")

        try:
            search = GoogleSearch(query_params)
            results = search.get_dict() # Get results as a dictionary
        except Exception as e:
            print(f"Error during SerpAPI call: {e}")
            return None # Or handle more gracefully

        if not results or "organic_results" not in results or not results["organic_results"]:
            print("No more results found or error in API response structure.")
            break

        for item in results.get("organic_results", []):
            if current_article_count >= num_articles_to_fetch:
                break

            title = item.get("title")
            link = item.get("link")
            doi = item.get("publication_info", {}).get("doi") # DOI might be in publication_info or need other extraction
            snippet = item.get("snippet") # Abstract snippet
            citation_count = item.get("inline_links", {}).get("cited_by", {}).get("total")

            # Authors and Journal/Year are often in 'publication_info.summary'
            publication_summary = item.get("publication_info", {}).get("summary", "")

            # Attempt to parse authors, year, journal from publication_summary
            # This is heuristic and might need refinement
            authors_str = "N/A"
            year_str = "N/A"
            journal_str = "N/A"

            parts = publication_summary.split(" - ")
            if len(parts) > 0:
                authors_str = parts[0] # Assuming authors are first
            if len(parts) > 1: # Journal and year might be here
                # Try to find year first
                year_match = pd.Series(parts[-1]).str.extract(r'(\b\d{4}\b)')
                if not year_match.empty and year_match.iloc[0,0] is not None :
                    year_str = year_match.iloc[0,0]
                    # If year is found, the rest of that part might be the journal
                    journal_candidate = parts[-1].replace(year_str, "").strip(" ,")
                    if journal_candidate:
                         journal_str = journal_candidate
                    elif len(parts) > 2 and year_str in parts[-1]: # e.g. Authors - Journal - Year
                        journal_str = parts[1]

                else: # If no year found in the last part, it might be the journal name itself
                    journal_str = parts[-1]


            article_data = {
                "Title": title,
                "Authors": authors_str,
                "Abstract_Snippet": snippet,
                "Year": year_str, # Will try to convert to int later if valid
                "Journal_Name": journal_str,
                "DOI": doi,
                "Source_Link": link,
                "Citation_Count": citation_count if citation_count is not None else 0
            }
            all_articles_data.append(article_data)
            current_article_count += 1

        page_num += 1
        if "pagination" not in results or "next" not in results["pagination"]: # No more pages
             if current_article_count < num_articles_to_fetch:
                print(f"Fetched all available results ({current_article_count}), which is less than preferred {num_articles_to_fetch}.")
             break


    if not all_articles_data:
        print("No articles were retrieved.")
        return pd.DataFrame()

    # Save raw data to JSON
    try:
        with open("outputs/retrieved_articles_raw.json", "w") as f:
            json.dump(all_articles_data, f, indent=4)
    except IOError as e:
        print(f"Error saving raw articles to JSON: {e}")

    # Convert to DataFrame
    df = pd.DataFrame(all_articles_data)

    # Attempt to convert Year to integer, coercing errors to NaT/NaN then to a default like 0 or keep as object
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').fillna(0).astype(int)
    df['Citation_Count'] = pd.to_numeric(df['Citation_Count'], errors='coerce').fillna(0).astype(int)

    return df

if __name__ == "__main__":
    main()
