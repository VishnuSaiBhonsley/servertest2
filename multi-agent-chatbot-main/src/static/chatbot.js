const chatContainer = document.getElementById("chat-container");
const chatBox = document.getElementById("chat-box");
const chatOptions = document.getElementById("chat-options");
const userInput = document.getElementById("user-input");

let session_id = "";
let userSelectedOptions = [];
let botResponses = {};

// Generate a random section ID
function generatesession_id() {
  return 'section-' + Math.random().toString(36).substr(2, 9);
}

// Initialize chatbot section ID
function initializeChatbot() {
  if (!session_id) {
    session_id = generatesession_id();
    console.log("Section ID generated:", session_id);
  }
}

// Fetch bot responses
async function fetchBotResponses(userText) {
  try {
    const response = await fetch('/getresponses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: userText, client_id: 'terralogic_academy',session_id:session_id })
    });
    
    if (!response.ok) throw new Error('Failed to fetch responses');
    botResponses = await response.json();
  } catch (error) {
    console.error('Error fetching bot responses:', error);
  }
}

// Add message to the chat
function addMessage(sender, text) {
  const messageElement = document.createElement("div");
  messageElement.classList.add("chat-message", sender);
  messageElement.textContent = text;
  chatBox.appendChild(messageElement);
  scrollToBottom();
}

// Show options for user selection
function showOptions(options) {
  chatOptions.innerHTML = "";
  const filteredOptions = options.filter(option => !userSelectedOptions.includes(option));
  filteredOptions.forEach(option => {
    const button = document.createElement("button");
    button.classList.add("option-button");
    button.textContent = option;
    button.onclick = () => handleOptionClick(option);
    chatOptions.appendChild(button);
  });
}

// Handle button click for user options
async function handleOptionClick(option) {
  addMessage("user", option);
  chatOptions.innerHTML = "";
  userSelectedOptions.push(option);
  await fetchBotResponses(option.toLowerCase());
  botReply(option.toLowerCase());
}

// Handle user-typed message
async function sendMessage() {
  const userText = userInput.value.trim().toLowerCase();
  if (!userText) return;

  addMessage("user", userText);
  userInput.value = "";
  userSelectedOptions.push(userText);
  await fetchBotResponses(userText);
  botReply(userText);
}

// Bot reply function
function botReply(userText) {
  const typingIndicator = createTypingAnimation();
  chatBox.appendChild(typingIndicator);

  setTimeout(() => {
    const botResponse = botResponses[userText];
    removeTypingAnimation(typingIndicator);
    if (botResponse) {
      addMessage("bot", botResponse.response);
      if (botResponse.options && botResponse.options.length > 0) {
        showOptions(botResponse.options);
      }
    } else {
      addMessage("bot", "I didn't understand that. Could you please rephrase?");
    }
  }, 1000);
}

// Toggle chatbot visibility
function toggleChatbot() {
  if (chatContainer.classList.contains("slideIn")) {
    chatContainer.classList.replace("slideIn", "slideOut");
    setTimeout(() => {
      chatContainer.style.display = "none";
      chatContainer.classList.remove("slideOut");
    }, 400);
  } else {
    chatContainer.style.display = "flex";
    chatContainer.classList.add("slideIn");
    if (!chatContainer.querySelector(".chat-logo")) {
      const logo = document.createElement("img");
      logo.src = "https://terralogic.com/wp-content/uploads/2022/12/favicon.png";
      logo.alt = "Chatbot Logo";
      logo.className = "chat-logo";
      chatContainer.insertBefore(logo, chatContainer.firstChild);
    }
  }
}

// Create typing animation
function createTypingAnimation() {
  const typingIndicator = document.createElement("div");
  typingIndicator.classList.add("typing-indicator");
  typingIndicator.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  return typingIndicator;
}

// Remove typing animation
function removeTypingAnimation(typingIndicator) {
  if (typingIndicator) typingIndicator.remove();
}

// Scroll to bottom of chat
function scrollToBottom() {
  chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
}

// Initialize chatbot on load
initializeChatbot();

// Event listener for Enter key
userInput.addEventListener("keypress", (event) => {
  if (event.key === "Enter") sendMessage();
});
