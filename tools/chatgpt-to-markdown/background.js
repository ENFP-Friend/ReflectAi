console.log("background.js: Service worker started/restarted.");

// Listen for messages from popup.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("background.js: Message received. Request:", request);

  if (request.action === "downloadMarkdown") {
    const topicName = request.filename;
    const chatGPTResponse = request.chatGPTText || ""; // Ensure it's a string

    if (!topicName || topicName.trim() === "") {
      console.error("background.js: Filename not provided in downloadMarkdown action.");
      sendResponse({ status: "failed", error: "Filename not provided." });
      return true; // Keep channel open for sendResponse
    }

    console.log(`background.js: 'downloadMarkdown' action received. Filename: "${topicName}"`);

    // Basic Markdown wrapping - use actual newlines \n
    const markdownContent = `# ${topicName}\n\n${chatGPTResponse}`;
    
    // Sanitize filename
    const safeTopicName = topicName.replace(/\\s+/g, '_').replace(/[^a-zA-Z0-9_.-]/g, '');
    const filename = `${safeTopicName || 'UntitledNote'}.md`;

    console.log(`background.js: Preparing download. Suggested filename: "${filename}", Content preview: "${markdownContent.substring(0, 70)}..."`);

    const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
    
    // Use FileReader to convert Blob to data URL for service worker context
    const reader = new FileReader();
    reader.onload = function() {
        const dataUrl = reader.result;
        chrome.downloads.download({
            url: dataUrl,
            filename: filename,
            saveAs: true // Prompts the user to choose a location
        }, (downloadId) => {
            if (chrome.runtime.lastError) {
                console.error("background.js: Download failed:", chrome.runtime.lastError.message);
                sendResponse({ status: "failed", error: chrome.runtime.lastError.message });
            } else {
                if (downloadId === undefined) {
                    console.warn("background.js: Download initiated, but downloadId is undefined.");
                    sendResponse({ status: "success_no_id" });
                } else {
                    console.log("background.js: Download started with ID:", downloadId);
                    sendResponse({ status: "success", downloadId: downloadId });
                }
            }
            // No need to revoke dataUrl like object URLs
        });
    };
    reader.onerror = function() {
        console.error("background.js: FileReader failed to read blob.");
        sendResponse({ status: "failed", error: "FileReader error." });
    };
    reader.readAsDataURL(blob);

    return true; // Indicates that sendResponse will be called asynchronously
  }
  
  // Handle other actions or return false if not handled
  console.log("background.js: Received message with unhandled action:", request.action);
  return false; 
});
