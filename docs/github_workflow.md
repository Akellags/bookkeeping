# GitHub Repository & Team Workflow Guide

This guide describes how to initialize the Help U repository, connect it to GitHub, and the standard branching/commit flow for developers.

---

## 🚀 1. Initial Repository Setup (One-Time)

*If you are the project owner and starting the repo for the first time:*

1.  **Initialize Git**: Open your terminal in the root `bookkeeper` directory.
    ```cmd
    git init
    ```
2.  **Add Files**: Stage all code and project files (except those ignored by `.gitignore`).
    ```cmd
    git add .
    ```
3.  **Initial Commit**:
    ```cmd
    git commit -m "Initial commit: GSTR-1 compliant backend and multi-tenant web onboarding"
    ```
4.  **Create GitHub Repo**:
    - Go to [GitHub](https://github.com/new).
    - Create a repository named `bookkeeper`.
    - **Do NOT** initialize with README, license, or gitignore (since we have them locally).
5.  **Link Local to GitHub**:
    *(Replace `YOUR_USER_NAME` with your actual GitHub username)*
    ```cmd
    git remote add origin https://github.com/YOUR_USER_NAME/bookkeeper.git
    git branch -M main
    git push -u origin main
    ```

---

## 🛠️ 2. Developer Workflow (Daily)

### 📥 Cloning the Repo (New Developers)
```cmd
git clone https://github.com/YOUR_USER_NAME/bookkeeper.git
cd bookkeeper
```

### 🌿 Creating a New Branch
**NEVER** commit directly to `main`. Always create a feature branch.
```cmd
# 1. Start from latest main
git checkout main
git pull origin main

# 2. Create branch (use naming: feat/, fix/, refactor/)
git checkout -b feat/your-feature-name
```

### 💾 Committing & Pushing
```cmd
# Stage changes
git add .

# Commit with a clear message
git commit -m "Brief description of changes"

# Push the branch to GitHub
git push -u origin feat/your-feature-name
```

---

## 🔄 3. Merging Changes

1.  **Pull Request (PR)**: Go to the GitHub repository page and click **"Compare & pull request"**.
2.  **Code Review**: Team members review the code and approve.
3.  **Merge**: Once approved, merge the PR on GitHub.
4.  **Clean up local**:
    ```cmd
    git checkout main
    git pull origin main
    git branch -d feat/your-feature-name
    ```

---

## ⚠️ 4. Crucial Git Rules
1.  **DO NOT commit sensitive files**: The `.env` and `.db` files are ignored by `.gitignore`. Never force add them.
2.  **Run Tests Before Pushing**: Ensure `main.py` starts up without errors.
3.  **Sync often**: Run `git pull origin main` frequently to avoid merge conflicts.
4.  **Descriptive Messages**: Use clear, actionable commit messages like `fix: resolve landing page spinner timeout` or `feat: add Stripe webhook for subscription updates`.
