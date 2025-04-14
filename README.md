# 🏛️ Advanced Court Document Analyzer

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-brightgreen.svg)
![Framework](https://img.shields.io/badge/framework-Streamlit-FF4B4B.svg)

An intelligent tool for extracting precise information from Supreme Court judgment PDFs using advanced text processing techniques. Turn unstructured legal documents into structured, actionable data.

## ✨ Features

- **Case Number Extraction** - Automatically detects primary and related case numbers with their components (type, nature, sequential number, year)
- **Party Identification** - Extracts petitioners and respondents from main and consolidated cases
- **Date Recognition** - Identifies judgment delivery dates with multiple format support
- **Constitutional Analysis** - Detects constitutional issues and challenged legislative acts
- **Background Context** - Extracts the core case background for quick understanding
- **Interactive Results** - View formatted reports directly in the browser
- **Multiple Export Options** - Save results as JSON, Markdown, or Excel for further analysis

## 🚀 Getting Started

### Prerequisites

```bash
python 3.12
```

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/Advanced-Court-Document-Analyzer.git
cd Advanced-Court-Document-Analyzer
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## 📊 Usage

Run the Streamlit app:

```bash
streamlit run app.py
```

Then navigate to http://localhost:8501 in your browser to access the application.

### Processing Documents

1. Upload one or more Supreme Court judgment PDFs using the file uploader
2. Choose between "Standard" or "Deep Analysis" extraction modes
3. View the extracted information displayed in the interface
4. Download individual results or all results in JSON, Markdown, or Excel format

## 🔍 How It Works

The analyzer uses a combination of techniques to extract information:

1. **PDF Text Extraction** - Preserves document layout while extracting text content
2. **Advanced Pattern Matching** - Uses specialized regex patterns for each type of information
3. **Structural Analysis** - Identifies document sections based on legal document conventions
4. **Data Modeling** - Uses Pydantic models to enforce structured data representation
5. **Format Flexibility** - Handles different judgment formats and writing styles

## 🧩 System Architecture

```
┌─────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  PDF Documents  │────▶│  Text Extraction  │────▶│ Pattern Matching │
└─────────────────┘     └───────────────────┘     └──────────────────┘
                                                           │
┌─────────────────┐     ┌───────────────────┐             ▼
│ Export Formats  │◀────│ Visualization &   │◀────┌──────────────────┐
└─────────────────┘     │ User Interface    │     │ Structured Data  │
                        └───────────────────┘     └──────────────────┘
```

## 📋 Example Output

The analyzer produces structured information including:

- **Case Numbers** with type, sequential number, and year
- **Party Information** categorized by role
- **Judgment Dates** in standardized format
- **Case Background** with key points extracted
- **Constitutional Issues** and challenged legislation

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [`LICENSE`](LICENSE ) file for details.

## 🔮 Future Enhancements

- Add support for more court document types beyond Supreme Court judgments
- Implement machine learning for improved entity recognition
- Add citation network analysis for related judgments
- Develop a dashboard for visualizing patterns across multiple judgments
- Add multi-language support for international court documents

---

*Made with ❤️ for legal professionals and researchers*
