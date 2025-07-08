from flask import Flask, render_template
import os

# Create Flask app with explicit template folder using absolute path
root_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(root_dir, 'templates')

print(f'DEBUG: Root directory: {root_dir}')
print(f'DEBUG: Template directory: {template_dir}')
print(f'DEBUG: Template directory exists: {os.path.exists(template_dir)}')
print(f'DEBUG: Template directory contents: {os.listdir(template_dir) if os.path.exists(template_dir) else "Directory not found"}')

app = Flask(__name__, template_folder=template_dir)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def index():
    print('DEBUG: Entered index route')
    print('DEBUG: Template directory:', app.template_folder)
    print('DEBUG: Available templates:', os.listdir(app.template_folder))
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True) 