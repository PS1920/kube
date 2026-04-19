
# Kubernetes AI Ops Visualizer

## AI-powered Kubernetes Debugging Assistant

Understanding what’s going wrong inside a Kubernetes cluster shouldn’t require digging through logs and commands. This system analyzes pod behavior and explains issues in a clear, human-readable way, along with practical steps to fix them.

---

## Overview

Kubernetes AI Ops Visualizer is designed to simplify debugging in Kubernetes environments. It retrieves real-time pod data, analyzes system behavior, and converts complex technical output into clear explanations.

The system is built with a backend-driven diagnostic engine and is designed to integrate with an interactive frontend for visualizing cluster state.

---

## Problem Statement

Debugging Kubernetes systems is often complex and time-consuming. Developers typically need to:

* Run multiple kubectl commands
* Manually inspect logs and system states
* Interpret low-level infrastructure behavior

This process slows down development and requires significant expertise.

---

## Solution

This project introduces a structured and simplified approach to debugging by:

* Collecting real-time Kubernetes pod data
* Analyzing logs and system metadata
* Detecting common failure patterns
* Explaining issues in simple terms
* Suggesting actionable fixes

The goal is to reduce manual effort and make system behavior easier to understand.

---

## Key Features

* Real-time Kubernetes cluster interaction using kubectl
* Automated detection of common pod failures
* Human-readable explanations of issues
* Actionable suggestions for resolution
* Confidence-based diagnostics
* Designed for integration with interactive visualization interfaces

---

## System Architecture

```
Frontend (React + Visualization Layer)
        ↓
Backend API (FastAPI)
        ↓
Kubernetes Cluster (Minikube)
        ↓
Diagnostic Engine
```

The frontend layer is designed to provide an interactive view of cluster components, enabling users to visually explore system behavior and inspect failures.

---

## How It Works

1. The backend queries the Kubernetes cluster using kubectl
2. Pod descriptions and logs are collected
3. The diagnostic engine analyzes patterns in the data
4. Failure scenarios are identified
5. A structured response is generated with explanation and suggested fix

---

## Example Workflow

### Step 1: Simulate a failure

```bash
kubectl create deployment broken-app --image=nginx:wrongtag
```

### Step 2: Query the system

```
GET /api/ask-ai?pod_name=broken-app
```

### Step 3: System response

```json
{
  "answer": "Kubernetes is unable to pull the container image required to start this pod.",
  "suggestion": "Ensure that the image name and tag are correct and that the container registry is accessible.",
  "confidence": "High"
}
```

---

## Tech Stack

* Backend: FastAPI (Python)
* Frontend (Planned): React with visualization (e.g., Three.js)
* Infrastructure: Kubernetes (Minikube)
* System Interaction: kubectl
* AI Layer: Rule-based diagnostic engine (extensible to LLMs)

---

## Project Structure

```
kube/
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── requirements.txt
├── frontend/   (planned)
├── README.md
```

---

## Setup Instructions

### 1. Navigate to backend

```bash
cd backend
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
python -m uvicorn main:app --reload
```

### 4. Access API documentation

```
http://127.0.0.1:8000/docs
```

---

## Why This Matters

Kubernetes provides powerful infrastructure capabilities but introduces significant complexity in debugging and system understanding.

This system reduces debugging effort by converting system-level behavior into clear, actionable insights, helping developers resolve issues faster and with greater confidence.

---

## Future Scope

* Integration with large language models for deeper reasoning
* Predictive failure detection
* Multi-cluster monitoring
* Fully interactive frontend for real-time cluster visualization

---



## Team

* Backend & AI: Vishnu B
* Frontend & Infrastructure:P S Shashank

