from flask import Flask, request, jsonify, render_template
from flask_cors import CORS # Ensure `graph.py` includes the `LollypopDesignGraph` class
import sys,os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Global variable for client_id
client_id = None
from src.graphs.graph import *
lollypop_design = LollypopDesignGraph()
lollypop_design.build_graph()

@app.route('/getresponses', methods=['POST'])
def get_responses():
    try:
        global client_id
        client_id = request.json.get('client_id')
        user_input = request.json.get('user_input')
        session_id=request.json.get('session_id')
        
        # Run graph function from LollypopDesignGraph instance
        output = lollypop_design.run_graph(user_input,session_id=session_id)

        # Format and display results
        def format_response(qa_data, user_input):
            if not qa_data:
                return {"error": "No data available."}
            return {
                user_input.lower(): {
                    "response": qa_data['chatbot_answer'],
                    'options': qa_data.get('llm_free_options', [])
                }
            }

        response = format_response(output, user_input)
        return jsonify(response)  # Return the response directly
        
    except Exception as e:
        print(f"Error: {e}")  # Log error for debugging
        return jsonify(error=str(e)), 500

@app.route('/')
def main():
    """Serve the main HTML interface."""
    return render_template("index.html")

@app.route('/lollypop_design')
def lollypop_design_page():
    """Serve the Lollypop Design HTML interface."""
    return render_template("lollypop_design.html")

@app.route('/lollypop_academy')
def lollypop_academy():
    """Serve the Lollypop Academy HTML interface."""
    return render_template("lollypop_academy.html")

@app.route('/terralogic_academy')
def terralogic_academy():
    """Serve the Terralogic Academy HTML interface."""
    return render_template("terralogic_academy.html")

if __name__ == "__main__":
    # Initialize the LollypopDesignGraph instance with session ID
    app.run(debug=True)
