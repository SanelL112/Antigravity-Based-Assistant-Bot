import re
with open('fix_bot_commands.py', 'r') as f:
    content = f.read()

# Add `import re` back, without triggering pyflakes unused import if we don't use it.
# Actually, `re` isn't used in this script, which is why pyflakes flagged it when I didn't delete it.
# Wait, I deleted `import re` using sed! So pyflakes SHOULD pass now!
