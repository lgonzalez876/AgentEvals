# Agent Morality Evaluations

A framework for evaluating moral decision-making in AI language models through ethical dilemma scenarios.

## Setup

### Prerequisites
- [Conda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution)

### Environment Setup

1. Create and activate the conda environment:
```bash
conda create -n agent_morality_eval python=3.13 -y
conda activate agent_morality_eval
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root with your API keys:

```env
# Required for different model providers
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
XAI_API_KEY=your_xai_api_key
```
