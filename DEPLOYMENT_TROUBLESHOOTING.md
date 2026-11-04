# Deployment Troubleshooting Guide

## Requirements.txt Issues

### Error: "Could not install requirements"

**Try these solutions in order:**

#### Solution 1: Use requirements-stable.txt
The main `requirements.txt` has exact versions from Windows. Some might not work on Linux.

```bash
# Rename files
mv requirements.txt requirements-exact.txt
mv requirements-stable.txt requirements.txt

# Commit and push
git add requirements.txt
git commit -m "Use stable requirements"
git push origin main
```

#### Solution 2: Remove problematic packages
Some packages might have version conflicts. Edit requirements.txt and remove:
- `torch==2.15.0` (if failing, sentence-transformers will install compatible version)
- Any packages with year 2026 in version (likely dev/nightly builds)

#### Solution 3: Use minimal requirements
```bash
# Use the minimal version
mv requirements-minimal.txt requirements.txt
git add requirements.txt
git commit -m "Use minimal requirements"
git push origin main
```

### Specific Package Errors

#### Error: "torch" installation failed
**Problem**: PyTorch is large and has platform-specific builds

**Solution**: Remove torch from requirements.txt. It will be installed automatically by sentence-transformers with the correct CPU version.

```txt
# Remove this line:
torch==2.15.0
```

#### Error: "pywin32" not found
**Problem**: pywin32 is Windows-only

**Solution**: Already removed from requirements.txt. If you see this error, ensure you're not using `pip freeze` output directly.

#### Error: Version "2026.x.x" not found
**Problem**: Some packages in your venv have dev/nightly versions

**Solution**: Replace with stable versions:
```txt
# Replace:
certifi==2026.10.23
# With:
certifi>=2024.0.0

# Replace:
regex==2026.9.29
# With:
regex>=2024.0.0
```

### Check Streamlit Cloud Logs

1. Go to Streamlit Cloud dashboard
2. Click on your app
3. Click "Manage app" → "Logs"
4. Look for the specific error message
5. Note which package is failing

## Common Deployment Errors

### Error 1: "ModuleNotFoundError"
**After successful install, app fails to import**

**Causes:**
- Missing package in requirements.txt
- Wrong package name

**Solution:**
```bash
# Check which package is missing
# Add it to requirements.txt
git add requirements.txt
git commit -m "Add missing package"
git push
```

### Error 2: "Memory limit exceeded"
**App crashes during startup or indexing**

**Causes:**
- Too many heavy packages
- Large initial data loading

**Solutions:**
1. Remove unused packages from requirements.txt
2. Don't load embeddings at startup (lazy load)
3. Reduce initial data

### Error 3: "Build timeout"
**Deployment times out during build**

**Causes:**
- Too many packages to install
- Slow package builds (like torch)

**Solutions:**
1. Use requirements-stable.txt (fewer dependencies)
2. Remove torch (let sentence-transformers handle it)
3. Split deployment into stages

## Step-by-Step Debugging

### Step 1: Identify the failing package
Look at Streamlit Cloud logs for lines like:
```
ERROR: Could not find a version that satisfies the requirement packagename
```

### Step 2: Check package availability
```bash
# On your local machine
pip search packagename
# or visit https://pypi.org/project/packagename/
```

### Step 3: Try compatible version
If exact version doesn't exist:
```txt
# Change from:
packagename==1.2.3
# To:
packagename>=1.2.0,<2.0.0
```

### Step 4: Test locally
```bash
# Create fresh venv
python -m venv test_venv
test_venv\Scripts\activate

# Install from your requirements.txt
pip install -r requirements.txt

# If it fails locally, fix it before deploying
```

## Alternative Requirements Files

### For Python 3.9 (if Streamlit Cloud uses older Python):
```txt
# Use requirements-py39.txt
# Lower versions that support Python 3.9
```

### For Python 3.11+ (current):
```txt
# Use requirements.txt (current file)
```

## Quick Fixes

### Fix 1: Simplify to essentials
```txt
streamlit
langchain
langchain-groq
langchain-chroma
langchain-huggingface
langgraph
chromadb
sentence-transformers
python-dotenv
GitPython
pypdf
mcp
```

### Fix 2: Let pip resolve versions
Remove all version pins and let pip install latest compatible versions:
```txt
streamlit>=1.0
langchain>=1.0
# etc.
```

### Fix 3: Use known working versions
```txt
streamlit==1.28.0
langchain==0.1.0
# etc. (older stable versions)
```

## If All Else Fails

### Nuclear Option: Fresh Start
1. Delete the app from Streamlit Cloud
2. Create new requirements.txt with ONLY essentials:
```txt
streamlit
langchain
langchain-groq
chromadb
sentence-transformers
GitPython
pypdf
mcp
```
3. Test locally first
4. Redeploy

### Contact Support
If none of these work:
1. Save your deployment logs
2. Post on Streamlit Community Forum
3. Include:
   - Error message
   - requirements.txt content
   - Python version
   - What you've tried

## Recommended Requirements.txt for Deployment

Based on your working venv, use `requirements-stable.txt`:
- ✅ Tested versions
- ✅ No Windows-specific packages
- ✅ No dev/nightly versions
- ✅ Compatible with Linux
- ✅ Smaller, faster install

## Testing Before Deploy

```bash
# Test in clean environment
python -m venv deploy_test
deploy_test\Scripts\activate
pip install -r requirements.txt

# If successful, deployment should work
# If fails, fix locally first
```

## Pro Tips

1. **Start minimal**: Deploy with minimal requirements first, add more later
2. **Pin major versions**: Use `package>=1.0,<2.0` instead of exact versions
3. **Test locally**: Always test requirements.txt in fresh venv before deploying
4. **Check logs**: Streamlit Cloud logs show exactly which package failed
5. **Use stable releases**: Avoid dev/rc/alpha versions

## Success Checklist

- [ ] requirements.txt has no Windows-specific packages (pywin32)
- [ ] requirements.txt has no dev versions (2026.x.x)
- [ ] All packages are available on PyPI
- [ ] Tested in fresh local venv
- [ ] File is named exactly `requirements.txt`
- [ ] File is in repository root
- [ ] File is committed and pushed to GitHub
