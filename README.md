# <p style= "text-align: center">🔐 Password Cracking Simulator (PCS) </p>

A lightweight and simplified simulator that demonstrates how password cracking can be accelerated using distributed systems principles. Built using Python and Flask, PCS uses a master-worker architecture to emulate real-world password cracking workflows—**ethically and safely** using only synthetic data. One can also say, a **distributed approach** in cracking passwords 

> [!NOTE]
> This project is meant for educational purposes **ONLY** and should never be/intended to be used for unethical purposes.

## Project Goals

- Demonstrate **task distribution** in distributed systems
- Showcase **worker coordination and resilience**
- Promote **security awareness** around password vulnerabilities
- Provide an **educational and ethical** tool to simulate password cracking

## Addressing Current System Issues

### Limitations in Existing Systems

| Problem | Limitation in Current Tools | PCS Solution |
|--------|-----------------------------|--------------|
| Complexity | Tools like Fitcrack require advanced setups (BOINC, GPUs) | Simplified architecture using Python + Flask |
| Ethical Concerns | Real tools use actual password hashes or cracked data | Only synthetic data used in PCS |
| Lack of Transparency | Tools are black-boxed, difficult to understand for learners | Full visibility into queueing, distribution, and logic |
| No Teaching Focus | Designed for performance, not pedagogy | Designed for student-friendly understanding and experimentation |
| Hidden Fault Behavior | Failures handled internally with no explanation | PCS (extensible) can simulate node failures and retries |

## Architecture
![Architecture Design](/assets/Architecture.jpg)

### Getting Started
1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/PCS.git`
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests: `python -m pytest test/`

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Use meaningful commit messages

### Running the Application
- Demo mode: `python start_pcs.py 2`
- GUI mode: `python gui_dashboard.py`
- Web dashboard: `python web_dashboard.py`
