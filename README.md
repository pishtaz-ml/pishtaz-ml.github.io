# Pishtaz - Theoretical Articles Platform

A modern website to share theoretical articles on Philosophy, History, Politics, Countries, and Economy.

## Features

*   **Dynamic Tabs**: Tabs are automatically generated from folders in the `articles/` directory.
*   **Easy Article Management**: Just drop Markdown files into the appropriate category folder.
*   **Modern Design**: Built with Tailwind CSS, featuring a clean red-themed interface.
*   **Responsive**: Works on desktop and mobile.

## How to Run

1.  **Prerequisites**: Python 3 installed.
2.  **Setup Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install flask markdown pyyaml
    ```
3.  **Run the Server**:
    ```bash
    python app.py
    ```
4.  **Open in Browser**: Visit `http://localhost:3000`.

## How to Add Articles

1.  Navigate to the `articles/` directory.
2.  Choose a category folder (e.g., `Philosophy`) or create a new one to add a new tab.
3.  Create a new Markdown file (e.g., `my-article.md`).
4.  Add metadata at the top of the file:
    ```markdown
    title: My Article Title
    date: 2023-10-27
    summary: A brief summary of the article.
    
    # My Article Title
    
    Here is the content of the article...
    ```
5.  Refresh the website.

## Customization

*   **Theme**: The color scheme is defined in `templates/base.html` using Tailwind configuration.
*   **Layout**: Edit `templates/` files to change the structure.
