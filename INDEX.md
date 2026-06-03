# Edge IoT System - Complete Documentation Index

Complete guide to all documentation for the Edge IoT project.

## Quick Navigation

### Getting Started (Start Here! 👈)

1. **[README.md](README.md)** - Project overview
2. **[SETUP.md](SETUP.md)** - Installation and initial setup (5 min)
3. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Understanding the project (15 min)

### Running the System

4. **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration options
5. **[API.md](API.md)** - REST API reference
6. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and fixes

### Deep Learning

7. **[DEVELOPMENT.md](DEVELOPMENT.md)** - How to develop (modify code)
8. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and internals
9. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete project understanding

### Testing & Operations

10. **[TESTING.md](TESTING.md)** - Testing procedures
11. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
12. **[PERFORMANCE.md](PERFORMANCE.md)** - Optimization and tuning

### Advanced Topics

13. **[EXTENDING.md](EXTENDING.md)** - Adding custom features
14. **[API.md](API.md)** - Advanced API usage

---

## Documentation by User Type

### 👤 I'm a Student Learning IoT

**Start here:**
1. README.md → Understand what this project does
2. SETUP.md → Get it running
3. PROJECT_SUMMARY.md → Learn how everything works
4. ARCHITECTURE.md → Deep understanding of design patterns
5. examples.py → See real usage examples

**Then explore:**
- DEVELOPMENT.md → Understand how code is organized
- EXTENDING.md → Try adding your own features

### 👨‍💼 I'm Operating This System in Production

**Start here:**
1. SETUP.md → Get it running
2. CONFIGURATION.md → Tune for your environment
3. DEPLOYMENT.md → Deploy properly
4. PERFORMANCE.md → Optimize for your workload

**Then bookmark:**
- TROUBLESHOOTING.md → Fix issues
- API.md → Monitor and integrate
- TESTING.md → Verify it works

### 👨‍💻 I'm a Developer Extending This System

**Start here:**
1. ARCHITECTURE.md → Understand design
2. DEVELOPMENT.md → Learn code organization
3. EXTENDING.md → Add custom features

**Then use as reference:**
- API.md → For integration
- examples.py → For patterns
- test_utils.py → For testing

### 🔧 I'm Troubleshooting Problems

**Start here:**
1. TROUBLESHOOTING.md → Find your issue
2. logs/ → Check system logs
3. PERFORMANCE.md → Check resource usage
4. TESTING.md → Verify functionality

---

## File Guide

### Core Application

```
bridge.py          # MQTT subscriber (main data processor)
app.py            # Flask web server (dashboard)
index.html        # Dashboard frontend
config.py         # Configuration (MQTT, thresholds, etc.)
log.json          # Persistent data storage
```

### Utility Modules

```
utils.py              # Common helper functions
config_validator.py   # Configuration validation
logger_setup.py       # Logging configuration
device_manager.py     # Device lifecycle management
data_aggregator.py    # Data aggregation and statistics
api_response.py       # API response formatting
metrics.py            # Performance monitoring
data_tools.py         # Export and analysis utilities
exceptions.py         # Custom exception hierarchy
test_utils.py         # Testing helpers
mqtt_utils.py         # MQTT utilities
cli.py                # Command-line interface
alerts.py             # Alert system
```

### Documentation

```
README.md              # Project overview
SETUP.md              # Installation guide
CONFIGURATION.md      # Configuration examples
API.md                # API reference
DEVELOPMENT.md        # Development guide
ARCHITECTURE.md       # System architecture
TROUBLESHOOTING.md    # Problem solving
PERFORMANCE.md        # Optimization guide
TESTING.md            # Testing procedures
DEPLOYMENT.md         # Production deployment
EXTENDING.md          # Custom development
PROJECT_SUMMARY.md    # Complete understanding
INDEX.md              # This file
```

### Test & Example Files

```
examples.py           # Usage examples
test_*.py            # Test files
send_varied_data.py  # Test data generator
```

---

## Common Workflows

### Workflow 1: Getting Started (30 minutes)

```bash
# 1. Install (5 min)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Understand (10 min)
cat README.md                    # Overview
cat PROJECT_SUMMARY.md | less   # Deep understanding

# 3. Run (5 min)
python bridge.py &              # Terminal 1
python app.py &                 # Terminal 2

# 4. Verify (5 min)
open http://localhost:5000      # Dashboard
python cli.py test-mqtt         # Connection test
python cli.py publish device-001 # Send data
```

### Workflow 2: Troubleshooting (15 minutes)

```bash
# 1. Identify the problem
# Look at TROUBLESHOOTING.md

# 2. Check logs
tail -f logs/bridge.log
tail -f logs/app.log

# 3. Run diagnostics
python cli.py test-mqtt          # MQTT?
python cli.py validate           # Log file?
curl http://localhost:5000/health # Flask?

# 4. Check system
ps aux | grep python
df -h                            # Disk space?
free -h                          # Memory?
```

### Workflow 3: Adding a Feature (1 hour)

```bash
# 1. Read the pattern
# EXTENDING.md → Find similar feature

# 2. Understand current code
# ARCHITECTURE.md → Understand design

# 3. Write code
# Follow patterns, add docstrings

# 4. Test
# python test_*.py
# python examples.py

# 5. Document
# Update EXTENDING.md with example
```

### Workflow 4: Deploying to Production (2 hours)

```bash
# 1. Plan deployment
cat DEPLOYMENT.md    # Choose approach

# 2. Prepare environment
cat CONFIGURATION.md # Configure for production

# 3. Deploy
# Follow DEPLOYMENT.md for your platform

# 4. Test
bash < TESTING.md    # Run test suite

# 5. Monitor
# Use PERFORMANCE.md metrics
```

---

## Key Concepts Reference

### Anomaly Detection
**See**: ARCHITECTURE.md → "Anomaly Detection Path"
**Learn**: PROJECT_SUMMARY.md → "Key Concepts" → "Anomaly Detection"
**Code**: bridge.py → `DeviceState.is_temp_anomaly()`

### Risk Scoring
**See**: ARCHITECTURE.md → "Risk Scoring Path"
**Learn**: PROJECT_SUMMARY.md → "Key Concepts" → "Risk Scoring"
**Code**: bridge.py → `score_risk()`

### Thread Safety
**See**: ARCHITECTURE.md → "Thread Model"
**Learn**: DEVELOPMENT.md → "Thread Safety"
**Code**: bridge.py → `with device_lock:`

### Data Flow
**See**: PROJECT_SUMMARY.md → "Data Flow End-to-End"
**Visualize**: ARCHITECTURE.md → Diagrams

---

## FAQ Quick Links

**Q: How do I change temperature thresholds?**
A: CONFIGURATION.md → "Temperature Thresholds"

**Q: How do I add a new sensor type?**
A: EXTENDING.md → "Adding New Sensor Types"

**Q: How do I fix MQTT connection errors?**
A: TROUBLESHOOTING.md → "MQTT Connection Issues"

**Q: How do I deploy to Docker?**
A: DEPLOYMENT.md → "Docker Deployment"

**Q: How do I monitor performance?**
A: PERFORMANCE.md → "System Resource Monitoring"

**Q: How do I test if it's working?**
A: TESTING.md → "Test Scenarios"

**Q: How do I understand the code?**
A: ARCHITECTURE.md or DEVELOPMENT.md

**Q: How do I add alerts?**
A: EXTENDING.md → "Adding Custom Alert Handlers"

---

## Learning Path (Recommended)

### Beginner (Week 1)
- Day 1: README → SETUP → Get running
- Day 2: PROJECT_SUMMARY → Understand concepts
- Day 3: examples.py → See patterns
- Day 4: API.md → Learn endpoints
- Day 5: TESTING.md → Run tests

**Goal**: Understand what the system does and how to use it

### Intermediate (Week 2-3)
- Day 1: ARCHITECTURE.md → System design
- Day 2: DEVELOPMENT.md → Code organization
- Day 3: EXTENDING.md → Add a simple feature
- Day 4: PERFORMANCE.md → Optimize
- Day 5: DEPLOYMENT.md → Deploy locally

**Goal**: Modify and deploy the system

### Advanced (Week 4+)
- Add custom sensors (EXTENDING.md)
- Integrate with external systems
- Deploy to cloud (DEPLOYMENT.md)
- Contribute improvements

**Goal**: Professional-level customization

---

## Documentation Statistics

| Document | Type | Length | Read Time |
|-----------|------|--------|-----------|
| README.md | Overview | ~ 500 lines | 5 min |
| SETUP.md | Guide | ~ 250 lines | 10 min |
| PROJECT_SUMMARY.md | Learning | ~ 650 lines | 20 min |
| DEVELOPMENT.md | Reference | ~ 250 lines | 15 min |
| ARCHITECTURE.md | Technical | ~ 650 lines | 30 min |
| API.md | Reference | ~ 300 lines | 15 min |
| TROUBLESHOOTING.md | Reference | ~ 500 lines | 20 min |
| PERFORMANCE.md | Guide | ~ 500 lines | 25 min |
| TESTING.md | Procedures | ~ 350 lines | 20 min |
| DEPLOYMENT.md | Guide | ~ 450 lines | 25 min |
| EXTENDING.md | Patterns | ~ 600 lines | 30 min |
| **Total** | | ~5,000 lines | ~3 hours |

---

## How to Use This Documentation

### Online Reading
Click links in any markdown document to navigate
Most tools auto-link references like `bridge.py`

### Offline Reading
```bash
# View in terminal
cat ARCHITECTURE.md | less

# Convert to PDF (requires pandoc)
pandoc ARCHITECTURE.md -o ARCHITECTURE.pdf

# Search content
grep -r "anomaly detection" .
```

### IDE Integration
Most IDEs support markdown preview:
- VS Code: Install Markdown Preview
- PyCharm: Built-in preview
- Vim: Use plugins like vim-markdown

---

## Getting Help

### Internal Resources
1. **Code Comments**: Read docstrings and inline comments
2. **Examples**: See examples.py for real usage
3. **Tests**: See test_*.py for expected behavior
4. **This Index**: Find the right document

### External Resources
1. **MQTT**: mqtt.org/faq
2. **Flask**: flask.palletsprojects.com/
3. **Python**: python.org/docs
4. **JSON**: json.org

---

## Contributing Improvements

Found something unclear? Want to improve docs?

1. Identify the issue
2. Update relevant document
3. Test your changes
4. Submit pull request

Thank you for improving this project! 🙏

---

**Last Updated**: 2024-01-15
**Version**: 1.0
**Maintained By**: Edge IoT Team
