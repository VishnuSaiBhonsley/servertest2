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
        client_id: 'lollypop_design',
      }),
    });
    
    if (!response.ok) throw new Error('Failed to fetch responses');
    
    // Merge new responses without resetting botResponses
    botResponses = { ...botResponses, ...await response.json() };
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
  botReply(userText);
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

    removeTypingAnimation(typingIndicator);
    
    if (botResponse) {
      addMessage("bot", botResponse.response);

      // If there are options, show them
      if (botResponse.options && botResponse.options.length > 0) {
        showOptions(botResponse.options);
      }
    } else {
      addMessage("bot", "I'm sorry, I didn't understand that. Could you please rephrase?");
    }
  }, 1000); // Simulate bot thinking time
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

    // Ensure section ID is generated when chatbot opens
    initializeChatbot();

    parent.postMessage({ action: "expand" }, "*");
  }
}

// Initialize the chatbot on load
initializeChatbot();

// Event listener for Enter key
userInput.addEventListener("keypress", handleKeyPress);
