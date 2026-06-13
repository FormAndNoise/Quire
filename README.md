# Coptic Print PDF Formatter

A desktop application designed to reformat standard PDF documents into ready-to-print **Coptic bookbinding** signatures. 

Instead of printing pages linearly (1, 2, 3...), this tool reorders them into nested sheets that can be folded in half and bound into booklets. 

## Features
* **Watch Folder Automation:** You don't need to manually import files into the app. Just use the standard "Print to PDF" option in Word, Chrome, or any other application, and save the file into the `Input` folder. The app detects it and reformats it instantly.
* **Custom Parcel Sizes:** Configure how many sheets of paper make up a single parcel (e.g., 3 sheets = 12 pages). The app automatically pads the end of the document with blank pages if needed.
* **Blackout Sheets:** Support for interleaved specialty paper. Designate specific sheets in a parcel as "Blackout Sheets", and the app will automatically insert blank pages into the text flow so your content perfectly skips over the specialty paper without losing the page sequence.
* **Manual vs. Auto Duplex:** Supports printers that handle automatic double-sided printing, as well as manual printers by splitting the output into `Front_Sides.pdf` and `Back_Sides.pdf`.

## Requirements
* Python 3.8+

## Installation
1. Clone or download this repository.
2. Open a terminal/command prompt in the project directory.
3. (Optional but recommended) Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
4. Activate the virtual environment:
   * **Windows:** `.venv\Scripts\activate`
   * **Mac/Linux:** `source .venv/bin/activate`
5. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## How to Use
1. Run the application:
   * **Windows:** Double-click the `start.bat` file, or run `python app.py` from your terminal.
   * **Mac/Linux:** Run `python app.py` from your terminal.
2. Configure your settings in the GUI (Sheets per Parcel, Blackout Sheets, Duplex mode).
3. Click **"Start Watching Input Folder"**. The app will create `Input`, `Output`, and `Processed` folders in the same directory.
4. Open any document you want to bind (Word, Web Browser, text file, etc.).
5. Print the document using your system's **"Print to PDF"** feature.
6. Save the resulting PDF into the newly created `Input` folder.
7. The app will immediately intercept the file, reformat it, and place the ready-to-print booklet into the `Output` folder. The original file will be moved to the `Processed` folder.

## Blackout Sheets Example
If your parcel is 3 sheets of paper (12 pages total), but you want the middle sheet (Sheet 2) to be black cardstock:
* Enter `2` in the Blackout Sheets field.
* The application will format the PDF so that pages 3, 4, 9, and 10 of the booklet are intentionally left blank, allowing you to feed your black cardstock into the printer safely.