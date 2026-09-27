# Contributing to BIS1

Thank you for considering contributing to the BIS1 project! This document outlines how you can help.

## How to Contribute

### Reporting Issues
Before submitting an issue, please check if it has already been reported. When you create an issue, please include:
- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs. actual behavior
- Any relevant screenshots or error messages
- Your environment details (OS, Python version, etc.)

### Suggesting Enhancements
Enhancement suggestions are welcome! Please provide:
- A clear title describing the enhancement
- Detailed description of the proposed feature
- Why this enhancement would be useful to users
- Any potential implementation considerations

### Submitting Pull Requests
1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes
4. Ensure your code follows the existing style and conventions
5. Add tests if applicable
6. Update documentation if needed
7. Submit a pull request with a clear description of your changes

## Development Setup

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.ai/) (for running the Llama 3 8B model)
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bis1.git
   cd bis1
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Ollama and pull the Llama 3 8B model:
   ```bash
   # Install Ollama from https://ollama.ai/
   ollama pull llama3:8b
   ```

4. Build the vector store:
   ```bash
   python scripts/build_vectorstore.py
   ```

5. Start the backend service:
   ```bash
   python backend/main.py
   ```

6. Access the frontend:
   Open `frontend/index.html` in your web browser or serve it with:
   ```bash
   python -m http.server 8080
   # Then visit: http://localhost:8080
   ```

## Code Style
- Follow PEP 8 for Python code
- Use descriptive variable and function names
- Add docstrings to functions and classes
- Keep lines to a maximum of 88 characters when possible
- Use 4 spaces for indentation (no tabs)

## Testing
- Run existing tests to ensure nothing is broken
- Add tests for new functionality
- Test both backend API and frontend functionality

## Documentation
- Keep the README updated with any changes
- Update API documentation if endpoints change
- Add inline comments for complex logic

## Community
- Be respectful and inclusive in all interactions
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Help others in the community when you can

Thank you for contributing to BIS1!