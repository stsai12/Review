# Research Article Review Pipeline

This project is a Python-based pipeline to automatically retrieve, filter, and synthesize peer-reviewed research articles.

## Features (Planned)

*   Retrieval from Google Scholar via SerpAPI.
*   Filtering by publication year, impact factor, and article type.
*   Metadata enrichment.
*   Thematic grouping of articles.
*   Automated generation of a scientific review article.
*   AI content detection and refinement.

## Setup

1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Prepare Input Data:**
    *   You will need a JSON file containing the scholarly article data. This file should be structured like a SerpAPI Google Scholar response, where the articles are in an array under the `"organic_results"` key.
    *   Place this file in the project root directory (e.g., as `input_articles.json`) or provide the path to the script when prompted.
    *   Each article object in the `"organic_results"` array should ideally contain fields like `title`, `link`, `snippet`, `publication_info.summary`, and `inline_links.cited_by.total`.
    *   **Journal Impact Factors (Optional but Recommended for Filtering):**
        *   For impact factor filtering, create a CSV file named `journal_impact_factors.csv` in the root directory of this project.
        *   The CSV file should have at least two columns: `Journal_Title` (for matching against journal names parsed from the JSON) and `Impact_Factor` (the numeric impact factor).
        *   An optional `ISSN` column can also be included for more accurate matching if available.
        *   Example `journal_impact_factors.csv`:
            ```csv
            Journal_Title,Impact_Factor,ISSN
            Nature,43.07,0028-0836
            Science,41.845,0036-8075
            PLoS ONE,2.74,1932-6203
            Journal of Lipid Research,4.505,0022-2275
            ```
        *   If this file is not found, impact factor filtering will be skipped.

## Usage

Run the main script:
```bash
python main.py
```
The script will prompt you for necessary inputs like search keywords, desired year range, etc.

## Project Structure

*   `main.py`: The main executable script for the pipeline.
*   `config.py`: Configuration settings (though API keys should ideally be environment variables).
*   `outputs/`: Directory where all generated files (data, review article) will be saved.
    *   `run_parameters.json`: The user-provided parameters for the pipeline run.
    *   `retrieved_articles_raw.json`: Raw articles fetched from SerpAPI.
    *   `articles_filtered_basic.json` / `.csv`: Articles after basic filtering.
    *   `articles_themed_placeholder.json` / `.csv`: Articles with placeholder themes. (Depends on completion of placeholder step)
    *   `articles_filtered_advanced.json` / `.csv`: Articles after advanced filtering (including impact factor if data provided). (Depends on completion of advanced filtering step)
    *   `generated_review_article_placeholder.md`: The placeholder Markdown output of the review article.
    *   `final_articles_for_review.json` / `.csv`: The final set of articles considered for the review.
    *   `article_summary_table.md`: A Markdown table summarizing the final articles.
*   `AGENTS.md`: Guidelines for AI agent development on this project.
*   `requirements.txt`: Python dependencies for the project.
*   `journal_impact_factors.csv` (User-provided): Optional file for impact factor filtering.
