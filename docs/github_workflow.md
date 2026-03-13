# Help U: Bookkeeping Repository & GitHub Workflow Guide

This guide describes how to initialize the **Bookkeeping** project repository, connect it to GitHub, and the standard branching/commit flow for developers.

---

## 🚀 1. Repository Initialization (Individual Project)

Each project in the Help U ecosystem (like `bookkeeping`) has its own dedicated GitHub repository. This allows for fine-grained access control and project-specific versioning.

### Initializing the Repository (One-Time)
1.  **Navigate to the project directory**:
    ```cmd
    cd helpU\bookkeeper
    ```
2.  **Initialize Git**:
    ```cmd
    git init
    ```
3.  **Add all files**:
    ```cmd
    git add .
    ```
4.  **Initial Commit**:
    ```cmd
    git commit -m "Initial commit: GSTR-1 compliant backend and multi-tenant web onboarding"
    ```
5.  **Connect to GitHub**:
    ```cmd
    git remote add origin https://github.com/Akellags/bookkeeping.git
    git branch -M main
    git push -u origin main
    ```

---

## 🔐 2. Access Management
- **Project Isolation**: Since each project has its own repo, you can invite developers only to the specific repositories they need.
- **Settings**: Manage collaborators via **Settings > Collaborators** in the GitHub repository.

---

## 🛠️ 3. Developer Workflow (Daily)

### 📥 Cloning the Project
```cmd
git clone https://github.com/Akellags/bookkeeping.git
cd bookkeeping
```

### 🌿 Feature Branching
**NEVER** commit directly to `main`. Always create a feature branch.
```cmd
# 1. Update main
git checkout main && git pull origin main

# 2. Create feature branch
# Format: feat/<desc> or fix/<desc>
git checkout -b feat/add-stripe-billing
```

### 💾 Committing & Pushing
```cmd
git add .
git commit -m "feat: implement stripe checkout session"
git push -u origin feat/add-stripe-billing
```

---

## 🔄 4. Merging Changes
1.  **Pull Request (PR)**: Create a PR on GitHub comparing your feature branch to `main`.
2.  **Code Review**: At least one other developer must review and approve.
3.  **Merge**: Once approved and tests pass, merge to `main`.

---

## ⚠️ 5. Critical Rules
1.  **Local Secrets**: Never commit `.env` or local database files. These are ignored by Git.
2.  **Run Tests**: Ensure the backend starts up correctly before pushing any code.
3.  **Sync often**: Run `git pull origin main` frequently to avoid merge conflicts.
