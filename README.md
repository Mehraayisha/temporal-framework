# Temporal Framework - 6-Tuple Contextual Integrity System

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic V2](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev/latest/)
[![Neo4j](https://img.shields.io/badge/neo4j-5.0+-red.svg)](https://neo4j.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready temporal contextual integrity framework implementing enhanced 6-tuple access control with graph database integration, comprehensive logging, and real-time policy evaluation.

## 🚀 Overview

The Temporal Framework extends traditional 5-tuple contextual integrity models with temporal dimensions, enabling time-aware privacy decisions in dynamic environments. Built for enterprise use cases requiring sophisticated access control with audit trails and emergency overrides.

### Key Features

#### ✅ **Currently Implemented**
- **🕐 Temporal-Aware Access Control**: 6-tuple model with time windows and context
- **🔒 Emergency Override System**: Medical/emergency access patterns
- **📝 Comprehensive Audit Logging**: Multi-level logging with security trails
- **⚡ Policy Evaluation Engine**: Rule-based decision making
- **🧪 Production-Ready**: Pydantic V2 validation, comprehensive testing
- **📊 Basic Graph Integration**: Neo4j and Graphiti foundation

#### 🚧 **In Development**
- **Advanced Graph Features**: Full Neo4j/Graphiti async integration
- **Performance Optimization**: Caching, metrics collection
- **Batch Processing**: Multi-request evaluation
- **🔧 Enterprise Integration**: Complete FastAPI service, containerization

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Mehraayisha/temporal-framework.git
cd temporal-framework

# Install dependencies using uv (recommended)
pip install uv
uv sync

# Run the main demo
uv run python main.py

# Or try the team onboarding demo
uv run python examples/team_onboarding_demo.py
```

## 📦 Installation

### Prerequisites

- **Python 3.12+** (required for modern typing features)
- **Neo4j Database** (local or remote instance)
- **UV Package Manager** (recommended) or pip

### Option 1: Using UV (Recommended)

```bash
# Install uv if not already installed
pip install uv

# Create and activate virtual environment with dependencies
uv sync

# Verify installation
uv run python -c "from core.tuples import EnhancedContextualIntegrityTuple; print('✅ Installation successful')"
```

### Option 2: Using Traditional pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from core.tuples import EnhancedContextualIntegrityTuple; print('✅ Installation successful')"
```

### Neo4j Setup

```bash
# Option 1: Docker (easiest)
docker run --name neo4j -p7474:7474 -p7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# Option 2: Neo4j Desktop or AuraDB
# Configure connection in .env file (see Configuration section)
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Neo4j Configuration
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="your_password"

# API Keys
OPENAI_API_KEY="sk-..."
GROQ_API_KEY="gsk_..."

# Environment
ENVIRONMENT="development"

# Team B Integration (optional)
GRAPHITI_MODE="team_b_api"  # Enable Team B organizational chart integration
TEAM_B_API_URL="http://localhost:8000"
```

### Team B Organizational Chart Integration (Optional)

The temporal-framework can integrate with **Team B's organizational chart API** as an optional data source. Team B runs as a **separate FastAPI service** and is not included in this repository.

**When to use:**
- You have Team B service running separately
- You need employee organizational context (department, manager, security clearance)
- You want to replace Graphiti as the org chart data source

**Setup:**
1. Start Team B service separately (see Team B documentation)
2. Set environment variables:
   ```bash
   GRAPHITI_MODE="team_b_api"
   TEAM_B_API_URL="http://localhost:8000"  # Team B's FastAPI server
   ```
3. Run temporal-framework: `python main.py`

The enricher will call Team B's HTTP API to fetch employee context. If Team B is unavailable, it automatically falls back to Graphiti.

See [TEAM_B_INTEGRATION.md](TEAM_B_INTEGRATION.md) for detailed integration guide.

**Default behavior:** If Team B environment variables are not set, temporal-framework uses Graphiti-core (included in this project).

## 🎯 Usage Examples

### Basic 6-Tuple Access Control

```python
from datetime import datetime, timezone, timedelta
from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext, TimeWindow
from core.policy_engine import TemporalPolicyEngine

# Create temporal context
time_window = TimeWindow(
    start=datetime.now(timezone.utc) - timedelta(hours=1),
    end=datetime.now(timezone.utc) + timedelta(hours=8),
    window_type="business_hours"
)

temporal_context = TemporalContext(
    service_id="medical_records",
    user_id="dr_smith", 
    location="ER_STATION_1",
    timezone="UTC",
    time_windows=[time_window],
    situation="EMERGENCY"
)

# Create 6-tuple access request
access_tuple = EnhancedContextualIntegrityTuple(
    data_type="patient_medical_record",
    data_subject="patient_12345",
    data_sender="emergency_physician",
    data_recipient="trauma_team", 
    transmission_principle="emergency_access",
    temporal_context=temporal_context
)

# Evaluate access request
policy_engine = TemporalPolicyEngine()
decision = policy_engine.evaluate_request(access_tuple)

print(f"Access Decision: {decision.allowed}")
print(f"Reason: {decision.reason}")
print(f"Confidence: {decision.confidence}")
```

### Emergency Override Scenario

```python
# Emergency scenario: After-hours patient access
emergency_context = TemporalContext(
    service_id="emergency_medical_system",
    user_id="oncall_physician",
    location="emergency_department",
    timezone="UTC", 
    situation="EMERGENCY",
    emergency_override=True  # Key difference
)

emergency_tuple = EnhancedContextualIntegrityTuple(
    data_type="critical_patient_data",
    data_subject="trauma_patient_001", 
    data_sender="emergency_physician",
    data_recipient="trauma_response_team",
    transmission_principle="life_safety_override",
    temporal_context=emergency_context,
    risk_level="HIGH",
    audit_required=True
)

# Emergency requests bypass normal time restrictions
decision = policy_engine.evaluate_request(emergency_tuple)
# Result: ALLOW (even outside business hours)
```

### Graph Database Integration

```python
from core.graphiti_manager import TemporalGraphitiManager

# Preferred: Graphiti knowledge graph (AI-enhanced queries)
graphiti_manager = TemporalGraphitiManager(
    server_url="https://graphiti.example",
    api_key="YOUR_API_KEY"
)
# await graphiti_manager.initialize()  # Async init where applicable

# Optional: Direct Neo4j manager (legacy/direct DB access). Use only if needed.
# from core.neo4j_manager import Neo4jConfig
# neo4j_manager = Neo4jConfig.get_company_manager(password="password")
# temporal_context.save_to_neo4j(neo4j_manager)
# entity_id = temporal_context.save_to_graphiti(graphiti_manager)
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   6-Tuple       │    │  Temporal       │    │  Policy         │
│   Data Model    │───▶│  Context        │───▶│  Engine         │
│                 │    │  Manager        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Pydantic      │    │  Graph Database │    │  Audit &        │
│   Validation    │    │  Integration    │    │  Logging        │
│                 │    │  (Neo4j/Graphiti)│   │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Classes

- **`TimeWindow`**: Temporal boundaries for access control
- **`TemporalContext`**: Rich contextual information with time awareness  
- **`EnhancedContextualIntegrityTuple`**: 6-tuple access control model
- **`TemporalPolicyEngine`**: Policy evaluation with temporal logic
- **`TemporalNeo4jManager`**: Neo4j graph database operations (optional)
- **`TemporalGraphitiManager`**: Graphiti AI knowledge graph integration

### Data Flow

1. **Request Creation**: Build 6-tuple with temporal context
2. **Validation**: Pydantic validates all fields and constraints
3. **Enrichment**: Add graph-based contextual information
4. **Policy Evaluation**: Apply temporal rules and policies
5. **Decision & Audit**: Log decision with full audit trail

## 📚 API Documentation

### Core Models

#### `EnhancedContextualIntegrityTuple`

The main 6-tuple model extending traditional 5-tuple with temporal awareness.

```python
class EnhancedContextualIntegrityTuple(BaseModel):
    # Core 6-tuple
    data_type: str                    # Type of data being accessed
    data_subject: str                 # Subject of the data  
    data_sender: str                  # Entity requesting access
    data_recipient: str               # Entity receiving data
    transmission_principle: str       # Governing principle
    temporal_context: TemporalContext # Temporal context (6th element)
    
    # Enhanced attributes
    risk_level: str = "MEDIUM"        # LOW, MEDIUM, HIGH, CRITICAL
    audit_required: bool = False      # Force audit logging
    compliance_tags: List[str] = []   # Regulatory compliance tags
    
    # Metadata
    session_id: Optional[str] = None  # Session tracking
    correlation_id: Optional[str] = None  # Cross-system correlation
```

#### `TemporalContext`  

Rich temporal context providing time-aware access control.

```python
class TemporalContext(BaseModel):
    # Core identifiers
    service_id: str                   # Requesting service
    user_id: str                     # User making request
    location: str                    # Physical/logical location
    timezone: str = "UTC"            # Timezone for time calculations
    
    # Temporal windows
    time_windows: List[TimeWindow] = []  # Valid time windows
    
    # Context flags
    emergency_override: bool = False     # Emergency access flag
    situation: str = "NORMAL"           # NORMAL, EMERGENCY, MAINTENANCE, etc.
    temporal_role: Optional[str] = None # Time-based role
```

### Policy Engine

#### `TemporalPolicyEngine`

Main policy evaluation engine with temporal logic support.

```python
# Initialize policy engine
policy_engine = TemporalPolicyEngine(
    config_file="mocks/rules.yaml",      # Path to YAML rules file
    neo4j_manager=neo4j_manager,         # Optional Neo4j integration
    graphiti_manager=graphiti_manager    # Optional Graphiti integration
)

# Evaluate access request
decision = policy_engine.evaluate_request(access_tuple)
```

#### Key Methods

- `evaluate_request(access_tuple)`: Evaluate 6-tuple access request
- `_load_rules()`: Load policy rules from configured source
- `save_rule_to_graphiti(rule)`: Save rule to Graphiti (if configured)
- `_load_rules_from_neo4j()`: Load rules from Neo4j (if configured)

## 🧪 Testing

The framework includes comprehensive test coverage:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_policy_engine.py -v  # Policy tests
uv run pytest tests/test_tuples.py -v         # Data model tests
uv run pytest tests/test_evaluator.py -v      # Evaluation tests

# Run tests with coverage (requires pytest-cov)
uv run pytest tests/ --cov=core --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing (25+ tests passing)
- **Integration Tests**: Neo4j and Graphiti basic integration
- **Policy Tests**: Access control rule validation  
- **Serialization Tests**: Pydantic model validation
- **Emergency Override Tests**: Critical access scenarios

### Current Test Status
- ✅ All 25 tests passing
- ✅ Pydantic V2 validation working
- ✅ Basic Neo4j integration tested
- 🚧 Advanced integration tests in development

## ⚠️ Current Limitations

While the framework is functional, please note these current limitations:

### Performance Features
- **No built-in caching**: Policy decisions are not cached (planned for v1.1)
- **No metrics collection**: Monitoring integration not yet implemented
- **Synchronous only**: Async support partially implemented
- **No batch processing**: Single request evaluation only

### Production Features
- **Basic error handling**: Enhanced error recovery in development
- **Limited monitoring**: Health checks and metrics endpoints planned
- **Manual scaling**: Auto-scaling and load balancing not implemented

### Integration Features
- **Graphiti integration**: Basic implementation, full async support in progress
- **Neo4j queries**: Basic operations, advanced graph analytics planned

See the [Roadmap](#🗺️-roadmap) section for planned improvements.

## 🔧 Configuration

Create a `.env` file for environment configuration:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Graphiti Configuration  
GRAPHITI_SERVER_URL=https://your-graphiti-server.com
GRAPHITI_API_KEY=your_api_key

# Logging Configuration
LOG_LEVEL=INFO
# Enable or disable audit logging (default: true). When disabled the
# framework will skip enqueueing audit records to minimize latency.
ENABLE_AUDIT=true
# Enable Prometheus metrics exposure (default: false). Set to true to
# attempt to register Prometheus metrics and start an HTTP exporter when
# ENABLE_METRICS is enabled in `main.py`.
ENABLE_METRICS=false
SECURITY_LOG_ENABLED=true

# Application Settings
EMERGENCY_OVERRIDE_ENABLED=true
DEFAULT_TIMEZONE=UTC
MAX_CONTEXT_AGE_HOURS=24
```

An example `.env` file demonstrating sensible defaults is provided as `.env.example` in the project root. Copy it to `.env` and edit values before running the demo.

## Audit sampling

To avoid unbounded audit write volume while preserving visibility, the audit subsystem supports sampling. Configure the `AUDIT_SAMPLE_RATE` value in your `.env` file to control how many decisions are recorded:

- `AUDIT_SAMPLE_RATE=1.0` — record all decisions (default)
- `AUDIT_SAMPLE_RATE=0.5` — record ~50% of decisions (sampling)
- `AUDIT_SAMPLE_RATE=0.0` — record none (useful for low-latency modes)

Sampling is applied at enqueue time; the framework performs best-effort sampling using a random sampler. Combine sampling with `ENABLE_AUDIT=false` for a full opt-out.

## 📊 Performance & Scalability

### Current Performance

- **Policy Evaluation**: Basic implementation, performance varies by complexity
- **Graph Queries**: Depends on Neo4j/Graphiti configuration and data size
- **Memory Usage**: Baseline usage, scales with data loaded
- **Throughput**: Depends on deployment configuration

### Basic Configuration

```python
# Current configuration options
policy_engine = TemporalPolicyEngine(
    config_file="mocks/rules.yaml",
    neo4j_manager=neo4j_manager,        # Optional Neo4j integration
    graphiti_manager=graphiti_manager    # Optional Graphiti integration
)
```

### Planned Performance Features

- Caching layer for policy decisions
- Metrics collection and monitoring
- Batch processing capabilities
- Performance benchmarking suite

## 🔐 Security Considerations

### Audit Logging

All access decisions are logged with:
- Full 6-tuple details
- Decision rationale  
- Timestamp and correlation IDs
- User and system context
- Emergency override usage

### Sensitive Data Handling

- No plaintext sensitive data in logs
- Encrypted graph database connections
- Configurable data retention policies
- GDPR/HIPAA compliance support

## 📈 Monitoring & Observability

### Logging Levels

```python
# Configure logging in your application
from core.logging_config import setup_logging

# Setup comprehensive logging
setup_logging(
    level="INFO",           # DEBUG, INFO, WARNING, ERROR
    enable_audit=True,      # Audit trail logging  
    enable_security=True,   # Security event logging
    log_file_path="logs/"   # Log directory
)
```

### Planned Metrics Integration

Future versions will support:
- **Prometheus**: Policy evaluation metrics (planned)
- **Grafana**: Dashboard visualization (planned)
- **ELK Stack**: Log aggregation and analysis  
- **Custom Metrics**: Application-specific monitoring (planned)

## 🗺️ Roadmap

### Version 1.1 (In Progress)
- [ ] **Performance Enhancement**: Add caching layer to policy engine
- [ ] **Metrics Collection**: Prometheus integration for monitoring
- [ ] **Batch Processing**: Evaluate multiple requests concurrently
- [ ] **Advanced Configuration**: Support for cache_ttl, max_concurrent_evaluations

### Version 1.2 (Planned)
- [ ] **Full Async Support**: Complete async/await integration
- [ ] **Health Endpoints**: `/health`, `/metrics`, `/status` API endpoints
- [ ] **FastAPI Service**: Production-ready REST API service
- [ ] **Performance Benchmarking**: Automated performance testing suite

### Version 2.0 (Future)
- [ ] **AI Policy Recommendations**: Machine learning for policy suggestions
- [ ] **Advanced Graph Analytics**: Complex relationship analysis
- [ ] **Multi-tenant Support**: Organization-level isolation
- [ ] **Real-time Monitoring Dashboard**: Web-based management interface

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup instructions
- Code style guidelines  
- Pull request process
- Testing requirements
- Documentation standards

### Quick Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/temporal-framework.git
cd temporal-framework

# Install development dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests before committing
uv run pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/Mehraayisha/temporal-framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Mehraayisha/temporal-framework/discussions)  
- **Documentation**: [Wiki](https://github.com/Mehraayisha/temporal-framework/wiki)
- **Email**: [Contact Team](mailto:team@temporal-framework.dev)

## 🙏 Acknowledgments

- Built on [Pydantic V2](https://docs.pydantic.dev/latest/) for data validation
- [Neo4j](https://neo4j.com/) for graph database capabilities
- [Graphiti](https://github.com/graphiti-ai/graphiti) for AI knowledge graphs
- Inspired by research in contextual integrity and temporal access control

---

## Integration Guide

The project includes a step-by-step integration guide for embedding the Privacy Firewall into other applications. See `INTEGRATION_GUIDE.md` in the repository root for platform-specific instructions, sample payloads, and troubleshooting steps. The guide prefers the Graphiti knowledge-graph when available; direct Neo4j usage is optional and only required for legacy setups.

---

**Built with ❤️ for enterprise privacy and access control**