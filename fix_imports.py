import os

for root, dirs, files in os.walk('backend'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'backend.app.' in content or 'backend.tests.' in content:
                content = content.replace('backend.app.', 'app.')
                content = content.replace('backend.tests.', 'tests.')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
