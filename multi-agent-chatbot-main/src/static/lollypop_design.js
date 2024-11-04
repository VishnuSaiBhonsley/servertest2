const chatContainer = document.getElementById("chat-container");
const chatBox = document.getElementById("chat-box");
const chatOptions = document.getElementById("chat-options");
const userInput = document.getElementById("user-input");

// Initialize a variable to store the section ID
let sectionId = "";

// List to track previously selected user inputs
let userSelectedOptions = [];

// Function to generate a random section ID
function generateSectionId() {
  return 'section-' + Math.random().toString(36).substr(2, 9); // Generates a random alphanumeric ID
}

// Ensure section ID is generated when the chatbot opens
function initializeChatbot() {
  if (!sectionId) {
    sectionId = generateSectionId(); // Generate and assign section ID
    console.log("Section ID generated:", sectionId); // Debugging log
  }
}

// Fetch predefined bot responses with keywords
let botResponses = {};

// Function to fetch bot responses (now corrected to be asynchronous)
async function fetchBotResponses(userText) {
  try {
    const response = await fetch('/getresponses', { // Update to your API endpoint
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        user_input: userText,
        client_id:'lollypop_design', // Corrected typo from userTex to userText
      }),
    });
    
    if (!response.ok) throw new Error('Failed to fetch responses');
    
    botResponses = await response.json(); // Await the JSON response
  } catch (error) {
    console.error('Error fetching bot responses:', error);
  }
}

// Function to add a message to the chat
function addMessage(sender, text) {
  const messageElement = document.createElement("div");
  messageElement.classList.add("chat-message", sender);
  messageElement.textContent = text;
  chatBox.appendChild(messageElement);
  scrollToBottom();
}

// Function to show button options for user to select
function showOptions(options) {
  chatOptions.innerHTML = ""; // Clear previous options

  // Filter options to exclude those that have already been selected
  const filteredOptions = options.filter(option => !userSelectedOptions.includes(option));

  filteredOptions.forEach(option => {
    const button = document.createElement("button");
    button.classList.add("option-button");
    button.textContent = option;
    button.onclick = () => handleOptionClick(option);
    chatOptions.appendChild(button);
  });
}

// Handle button click and bot reply
async function handleOptionClick(option) {
  addMessage("user", option);
  chatOptions.innerHTML = ""; // Hide options after user clicks one

  // Add the selected option to the list of user-selected options
  userSelectedOptions.push(option);

  await fetchBotResponses(option.toLowerCase()); // Await fetch response
  botReply(option.toLowerCase());
}

// Function to handle user-typed message
async function sendMessage() {
  const userText = userInput.value.trim().toLowerCase();
  if (userText === "") return;

  addMessage("user", userText);
  userInput.value = ""; // Clear input field

  // Add the typed message to the list of user-selected options
  userSelectedOptions.push(userText);

  await fetchBotResponses(userText); // Await the response from fetchBotResponses

  // Check for matches with keywords in botResponses
  const matchedOptions = Object.keys(botResponses).filter(key => userText.includes(key));

  if (matchedOptions.length > 0) {
    // If there's a match, respond with the first match found
    botReply(matchedOptions[0]);
  } else {
    // If no matches, make an HTTP request
    await makeHttpRequest(userText); // Await the request
  }
}

// Handle pressing Enter key
function handleKeyPress(event) {
  if (event.key === "Enter") {
    sendMessage();
  }
}

// Function to generate bot reply based on user input
function botReply(userText) {
  const typingIndicator = createTypingAnimation();
  chatBox.appendChild(typingIndicator);
  setTimeout(() => {
    // Check for predefined responses
    const botResponse = botResponses[userText];

    if (botResponse) {
      removeTypingAnimation(typingIndicator);
      addMessage("bot", botResponse.response);

      // If there are options, show them
      if (botResponse.options && botResponse.options.length > 0) {
        showOptions(botResponse.options);
      }
    } else {
      addMessage("bot", "I didn't understand that. Could you please rephrase?");
    }
  }, 1000); // Simulate bot thinking time
}

// Function to make HTTP request for user input
async function makeHttpRequest(userText) {
  // Ensure section ID is generated
  if (!sectionId) {
    sectionId = generateSectionId(); // Generate and assign section ID if not already generated
  }

  const typingIndicator = createTypingAnimation();
  chatBox.appendChild(typingIndicator);

  try {
    const response = await fetch('/ask', { // Update to your API endpoint
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        user_input: userText,
        section_id: sectionId, // Pass the section ID with the request
        client_id:'lollypop_design', 
        model_choice: "google" // Corrected typo from "gogle"
      }),
    });

 // Check if the response is OK
 if (!response.ok) {
  throw new Error('Network response was not ok');
}

// Convert the response to JSON
const data = await response.json();

// Access the 'response' property correctly
if (data.response) {
  removeTypingAnimation(typingIndicator);
  addMessage("bot", data.response); // Display the bot's response

  // Show the first option by default if available in botResponses
  const options = botResponses[Object.keys(botResponses)[0]].options;
  if (options && options.length > 0) {
    showOptions(options); // Display options
  }
} else {
  removeTypingAnimation(typingIndicator);
  addMessage("bot", "I did not get a valid response from the server.");
}
} catch (error) {
removeTypingAnimation(typingIndicator);
console.error('Error:', error); // Log the error for debugging
addMessage("bot", "Sorry, I could not reach the server. Please try again later.");
}
}

function createTypingAnimation() {
  const typingIndicator = document.createElement("div");
  typingIndicator.classList.add("typing-indicator");
  typingIndicator.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  return typingIndicator;
}

function removeTypingAnimation(typingIndicator) {
  // Remove the specific typing animation element
  if (typingIndicator) {
    typingIndicator.remove();
  }
}

// Scroll to the bottom of the chat
function scrollToBottom() {
  chatBox.scrollTo({
    top: chatBox.scrollHeight, // Scroll to the bottom
    behavior: "smooth" // Add smooth scrolling animation
  });
}

// Toggle chatbot visibility
function toggleChatbot() {
  if (chatContainer.classList.contains("slideIn")) {
    // Hide the chat container with animation
    chatContainer.classList.remove("slideIn");
    chatContainer.classList.add("slideOut");

    setTimeout(() => {
      chatContainer.style.display = "none";
      chatContainer.classList.remove("slideOut");
    }, 300); 

    parent.postMessage({ action: "collapse" }, "*");
  } else {
    // Show the chat container with animation
    chatContainer.classList.remove("slideOut"); // Remove slideOut if it's there
    chatContainer.style.display = "flex"; 
    chatContainer.classList.add("slideIn");

    parent.postMessage({ action: "expand" }, "*");
  }
}

// Initialize the chatbot on load
initializeChatbot();

// Event listener for Enter key
userInput.addEventListener("keypress", handleKeyPress);
