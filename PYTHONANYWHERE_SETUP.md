# PythonAnywhere Setup Guide

## Media Files & Static Files Configuration

### Issue
- 404 errors for `/media/avatars/` files
- 404 errors for `/static/icons/` files

### Solution

#### Step 1: Collect Static Files
On PythonAnywhere, run in the Bash console:
```bash
cd ~/afyacom.pythonanywhere.com/
source venv/bin/activate
python manage.py collectstatic --no-input
```

#### Step 2: Configure Web App

Go to **Web** tab in PythonAnywhere dashboard and configure:

**Static files mapping:**
- URL: `/static/`
- Directory: `/home/afyacom/afyacom.pythonanywhere.com/staticfiles/`

**Static files mapping:**
- URL: `/media/`
- Directory: `/home/afyacom/afyacom.pythonanywhere.com/media/`

#### Step 3: Ensure media directory permissions
```bash
chmod -R 755 ~/afyacom.pythonanywhere.com/media/
chmod -R 755 ~/afyacom.pythonanywhere.com/staticfiles/
```

#### Step 4: Reload Web App
- Click **Reload** button in the Web tab

### What Each Setting Does

| Setting | Path | Purpose |
|---------|------|---------|
| `/static/` | `staticfiles/` | Django collectstatic output |
| `/media/` | `media/` | User-uploaded files (avatars, images, docs) |

### Verification

After setup, test:
1. Upload an avatar - should appear in profile
2. Check Network tab in DevTools
3. `/media/avatars/` files should return 200, not 404

### Django Settings (Already Configured)

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = 'static/'
STATICFILES_DIRS = [...]
STATIC_ROOT = BASE_DIR / "staticfiles"
```

### Troubleshooting

**Still getting 404?**
- Verify directory paths match exactly in PythonAnywhere Web config
- Ensure directories are owned by `afyacom` user
- Check file permissions: `ls -la ~/afyacom.pythonanywhere.com/media/`
- Reload web app after any changes

**Icons missing?**
- Ensure PNG files exist in `mobile_app/web/` or `static/icons/`
- Run `collectstatic` again if files were added
- Check that `STATICFILES_DIRS` includes the correct path

**Avatar upload fails?**
- Check `media/` directory is writable: `touch media/test.txt`
- Verify form uses `enctype="multipart/form-data"`
- Check Django logs for upload errors
