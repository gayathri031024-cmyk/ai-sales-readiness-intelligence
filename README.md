AI Sales Readiness Intelligence

AI-powered sales simulation, competency evaluation, and readiness coaching platform.

AI Sales Readiness Intelligence simulates realistic sales conversations with an adaptive AI buyer, evaluates representative behavior using conversation evidence, and produces explainable readiness decisions through a deterministic evaluation and rules engine.

Instead of relying on an opaque LLM-generated score, the platform separates AI-based interpretation from deterministic business logic, making evaluation more explainable, testable, and auditable.

Live Demo: Try AI Sales Readiness Intelligence

Tech Stack: React · TypeScript · FastAPI · PostgreSQL · LangGraph · Anthropic Claude · Alembic

---

What This Project Demonstrates

Full-stack application development with React and FastAPI
REST API design and backend architecture
PostgreSQL database design and migrations
LLM integration using Anthropic Claude
LangGraph-based AI workflow orchestration
Evidence-based AI evaluation
Deterministic business rules and decision logic
Retrieval-Augmented Generation (RAG)
Citation verification and grounded responses
Competency dependency analysis
Automated backend testing
GitHub Actions CI
Production deployment

---

Product Overview

Sales training platforms can generate conversations and scores, but a score alone does not explain why a representative is ready or where they need improvement.

This project addresses that problem by combining AI interpretation with deterministic evaluation logic.

Scenario
   ↓
Adaptive AI Buyer
   ↓
Sales Conversation
   ↓
Evidence Extraction
   ↓
Competency Evaluation
   ↓
Deterministic Readiness Engine
   ↓
Readiness Decision
   ↓
Coaching & Targeted Practice
Core Design Principle

The LLM does not directly determine sales readiness.

The LLM is used for tasks such as conversation understanding, evidence interpretation, and generating coaching content.

The final readiness decision is produced by deterministic business rules operating on structured evaluation results.

This separation improves:

Explainability
Testability
Reproducibility
Auditability
Control over business decisions

---

Key Features

🤝 Adaptive AI Buyer

Simulates multi-turn sales conversations within defined customer, product, and scenario constraints.

The AI buyer adapts its responses based on the representative's conversation behavior while remaining within the configured scenario.

🔎 Evidence-Based Evaluation

Analyzes sales conversations and evaluates representative behavior using specific conversation evidence rather than relying only on an overall AI-generated score.

🎯 Deterministic Readiness Engine

Converts evaluated competencies and evidence into an explicit readiness decision using deterministic business rules.

This keeps the final business decision separate from the LLM.

🧠 AI Coaching

Generates targeted coaching based on identified competency weaknesses and supporting conversation evidence.

🏋️ Targeted Practice Drills

Creates focused practice opportunities around identified skill gaps so representatives can work on specific competencies.

📈 Adaptive Difficulty

Provides recommendations for adjusting practice difficulty based on evaluation results and competency performance.

📚 Product Knowledge RAG

Supports product-knowledge questions using retrieved information and citation verification to improve grounding and reduce unsupported responses.

🕸️ Skill Graph & Root-Cause Analysis

Uses a deterministic competency dependency graph to identify related skill weaknesses within a conversation.

The system intentionally distinguishes correlation and dependency analysis from causal claims.

---

Example Evaluation Flow

A typical evaluation follows this process:

Sales Representative
        ↓
AI Buyer Conversation
        ↓
Conversation Evidence
        ↓
Competency Evaluation
        ↓
Structured Competency Results
        ↓
Deterministic Rules
        ↓
Readiness Decision
        ↓
Coaching / Practice Recommendations

This architecture allows the AI components to assist with interpretation while keeping important business decisions controlled by explicit application logic.

---

Architecture

The application separates the frontend, backend, AI orchestration, evaluation logic, and persistence layers.

---

Technical Stack

Layer	Technology
Frontend	React, TypeScript
Backend	Python, FastAPI
Database	PostgreSQL
AI Orchestration	LangGraph
LLM	Anthropic Claude
Validation	Pydantic
Database Migrations	Alembic
Testing	pytest
CI	GitHub Actions
Deployment	Vercel, Render

---

Engineering Highlights

AI + Deterministic Business Logic

The project deliberately separates probabilistic LLM interpretation from deterministic readiness decisions.

LLM
 ↓
Interpretation / Evidence
 ↓
Structured Evaluation
 ↓
Deterministic Rules
 ↓
Final Readiness Decision

This makes the system easier to reason about, test, and evolve.

Multi-Stage Evaluation Pipeline

The backend implements an explicit pipeline from:

Scenario → Conversation → Evidence → Evaluation → Readiness → Coaching

Dependencies between stages are checked explicitly rather than silently assuming that required computations have already been performed.

Grounded RAG

The product-knowledge workflow retrieves relevant information and verifies citations before returning grounded responses.

Competency Dependency Analysis

A deterministic skill graph identifies relationships between competency weaknesses to support more targeted coaching and practice.

Database Migrations

Database schema changes are managed through Alembic migrations rather than relying on manual database modifications.

Automated Testing

The backend includes automated tests covering core application behavior, evaluation logic, API workflows, and deterministic degradation paths for LLM-dependent components.

CI

GitHub Actions is used to automate project validation and testing.

---

API

The FastAPI backend provides REST endpoints for the major application workflows.

Health & Scenarios
GET  /health
GET  /scenarios
Conversations
POST /conversations
POST /conversations/{id}/turns
POST /conversations/{id}/evaluate
POST /conversations/{id}/readiness
Coaching & Practice
POST /conversations/{id}/coaching
POST /conversations/{id}/drill
Product Knowledge
POST /knowledge/documents
POST /knowledge/query
Skill Analysis
GET /conversations/{id}/root-cause-analysis

Request and response schemas are defined using Pydantic models in the backend.

---

Running Locally

Backend

cd backend

pip install -r requirements.txt

cp .env.example .env

alembic upgrade head

uvicorn app.main:app --reload
Frontend
cd frontend

npm install

npm run dev

The frontend development server proxies /api/* requests to the local FastAPI backend.

Environment Variables

Create the environment file from the provided example:

cp backend/.env.example backend/.env

Add your own local credentials and configuration values.

Never commit API keys, passwords, database credentials, or other secrets to the repository.

---

Testing

The project includes an automated backend test suite using pytest.

LLM-dependent components also support deterministic degradation paths so that important parts of the application can be tested without requiring live external API calls.

Run the repository's configured test commands to validate the current implementation.

---

Current Product Scope

The current version focuses on the core sales-readiness evaluation pipeline:

Scenario management
Adaptive AI buyer
Multi-turn conversations
Evidence extraction
Competency evaluation
Deterministic readiness evaluation
AI coaching
Targeted practice drills
Adaptive difficulty recommendations
Product-knowledge RAG
Competency dependency analysis

The MVP intentionally focuses on the core evaluation workflow rather than attempting to implement every possible enterprise sales-readiness feature.

---

Future Direction

Potential future extensions include:

Longitudinal representative performance tracking
Cross-conversation "Sales DNA" analysis
Expanded scenario libraries
Production authentication and authorization
Multi-tenant architecture
Complete frontend workflows for coaching, drills, and RAG
Advanced analytics and reporting

These are planned product extensions rather than requirements for the current core evaluation pipeline.

---

## Project Documentation

For deeper technical details:

* [`ARCHITECTURE.md`](ARCHITECTURE.md)
* [`DATA_MODEL.md`](DATA_MODEL.md)
* [`DECISIONS.md`](DECISIONS.md)
* [`TEST_STATUS.md`](TEST_STATUS.md)
* [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)
* [`PROJECT_PLAN.md`](PROJECT_PLAN.md)

---

## Live Demo

**Try the application:**
https://ai-sales-readiness-intelligence.vercel.app/

---

