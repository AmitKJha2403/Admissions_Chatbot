from flask import Flask, render_template, request
import openai
import time
import os

app = Flask(__name__)

# Set your OpenAI Assistant ID here
assistant_id = os.getenv("ASSISTANT_ID")

# Initialize the OpenAI client (ensure to set your API key in the sidebar within the app)
client = openai
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai.api_key=api_key

# Initialize session state variables for file IDs and chat control
file_id_list = []
start_chat = False
thread_id = None

# Process messages with citations
def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    message_content = message.content[0].text
    annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

        # Gather citations based on annotation attributes
        if (file_citation := getattr(annotation, 'file_citation', None)):
            # Retrieve the cited file details (dummy response here since we can't call OpenAI)
            cited_file = {'filename': 'cited_document.pdf'}  # This should be replaced with actual file retrieval
            citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            # Placeholder for file download citation
            cited_file = {'filename': 'downloaded_document.pdf'}  # This should be replaced with actual file retrieval
            citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')  # The download link should be replaced with the actual download path

    # Add footnotes to the end of the message content
    full_response = message_content.value + '\n\n' + '\n'.join(citations)
    return full_response


# Generate OpenAI response
def generate_openai_response(prompt):
    global thread_id
    thread = client.beta.threads.create()
    thread_id = thread.id

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="Please answer the queries using the knowledge provided in the files. When adding other information, mark it clearly as such with a different color."
    )

    while True:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run.status == 'completed':
            break

    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )

    assistant_responses = []
    assistant_messages_for_run = [
        message for message in messages
        if message.run_id == run.id and message.role == "assistant"
    ]

    for message in assistant_messages_for_run:
        full_response = process_message_with_citations(message)
        assistant_responses.append(full_response)

    return assistant_responses

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    global start_chat
    if request.method == 'POST':
        user_message = request.form['user_message']
        if start_chat:
            assistant_responses = generate_openai_response(user_message)
            return render_template('index.html', user_message=user_message, assistant_responses=assistant_responses)
        else:
            start_chat = True
            return render_template('index.html', start_chat=start_chat)
    else:
        return render_template('index.html', start_chat=start_chat)

if __name__ == '__main__':
    app.run(debug=True)