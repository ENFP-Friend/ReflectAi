(() => {
  // This is a common structure, but might need adjustment if ChatGPT's UI changes.
  // We're looking for elements that typically contain a response.
  // This selector aims for a common pattern where responses are rendered in divs
  // that are part of a "group" and often contain paragraphs or specific data attributes.
  // A more robust selector might target elements with role="button" inside message containers,
  // as ChatGPT often has copy buttons or similar interactive elements near the text.
  
  // Attempt to find the last assistant message. Selectors are highly dependent on ChatGPT's current HTML.
  // These are educated guesses and may need refinement.
  let lastResponseText = "ERROR: Could not find the last ChatGPT response text with current selectors.";
  let found = false;

  // Try a more specific selector first (common pattern for assistant messages)
  // This looks for a message group from the assistant, then the markdown content within.
  // Often, messages are in a container with a data-attribute indicating the author role.
  let selectors = [
    // Common pattern: a message from assistant, then a div containing the rendered markdown
    'div[data-message-author-role="assistant"] div.markdown', 
    // Another common pattern: a message group, then a child that's specifically the result text
    'div.group.w-full .text-base > div > div.markdown', // More specific to a common layout
    // General class for rendered markdown content, hoping the last one is the response
    'div.prose', 
    // Previous selectors as fallbacks
    'div.group div.markdown', 
    'div[class*="ConversationItem__Message"] div[class*="markdown"]'
  ];

  for (const selector of selectors) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      const lastElement = elements[elements.length - 1];
      // Prefer innerHTML to try and capture formatting
      if (lastElement && lastElement.innerHTML) { 
        lastResponseText = lastElement.innerHTML;
        console.log(`content.js: Found HTML content using selector: "${selector}"`);
        found = true;
        break; // Stop if we found something
      } else if (lastElement && (lastElement.innerText || lastElement.textContent)) {
        // Fallback to innerText if innerHTML is empty (less likely for formatted content)
        lastResponseText = lastElement.innerText || lastElement.textContent;
        console.log(`content.js: Found plain text using selector (innerHTML was empty): "${selector}"`);
        found = true;
        break; 
      }
    }
  }

  if (!found) {
    console.warn("content.js: None of the selectors found the ChatGPT response text. Returning default error message.");
  }
  
  // Explicitly return the extracted text. This will be available in the 'result' property
  // of the object in the 'results' array passed to the executeScript callback.
  return lastResponseText.trim();
})();
