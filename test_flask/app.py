from flask import Flask, render_template
import os

# Get absolute paths
root_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(root_dir, 'templates')

print(f'Starting Flask app with:')
print(f'Root directory: {root_dir}')
print(f'Template directory: {template_dir}')
print(f'Template directory exists: {os.path.exists(template_dir)}')
if os.path.exists(template_dir):
    print(f'Template directory contents: {os.listdir(template_dir)}')

# Create Flask app with explicit template folder
app = Flask(__name__, template_folder=template_dir)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def index():
    try:
        return render_template('home.html')
    except Exception as e:
        print(f'Error rendering template: {str(e)}')
        print(f'Current working directory: {os.getcwd()}')
        print(f'Template folder from app: {app.template_folder}')
        if app.jinja_loader:
            print(f'Template list: {app.jinja_loader.list_templates()}')
        else:
            print('No jinja_loader available')
        return f'Error: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True) 