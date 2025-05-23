document.addEventListener('DOMContentLoaded', () => {
  const filenameInput = document.getElementById('filename');
  const saveButton = document.getElementById('saveButton');
  const statusP = document.getElementById('status');

  saveButton.addEventListener('click', async () => {
    const topicName = filenameInput.value.trim();
    if (!topicName) {
      statusP.textContent = 'Please enter a filename.';
      return;
    }

    statusP.textContent = 'Processing...';
    saveButton.disabled = true;

    try {
      // Get the current active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab || !tab.id) {
        statusP.textContent = 'Could not get active tab.';
        saveButton.disabled = false;
        return;
      }
      
      // Check if the URL is a restricted one where content scripts can't run
      if (tab.url && (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://") || tab.url.startsWith("about:"))) {
        statusP.textContent = 'Cannot run on this special page.';
        console.warn(`popup.js: Attempting to run on a restricted page: ${tab.url}.`);
        saveButton.disabled = false;
        return;
      }

      // Inject content.js and expect a result
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js'] 
        // We'll modify content.js to return the text directly
      });

      if (chrome.runtime.lastError) {
        statusP.textContent = 'Error injecting script.';
        console.error('Error injecting content.js:', chrome.runtime.lastError.message);
        saveButton.disabled = false;
        return;
      }

      // content.js should be modified to return the text as the last expression's result
      if (results && results[0] && results[0].result !== undefined) {
        const chatGPT_HTML_Response = results[0].result;
        statusP.textContent = 'HTML extracted. Converting to Markdown...';

        let markdownText = "Error: Turndown service not available or conversion failed.";
        if (typeof TurndownService !== 'undefined') {
          try {
            const turndownService = new TurndownService({
              headingStyle: 'atx', // # Heading
              hr: '---',
              bulletListMarker: '*', // For regular lists
              codeBlockStyle: 'fenced', // ```code```
              emDelimiter: '*', 
              fence: '```' // Ensure ``` is used for code blocks
            });

            // Rule to handle paragraphs inside list items to prevent extra newlines
            turndownService.addRule('paragraphInLi', {
              filter: function (node) {
                return node.nodeName === 'P' && node.parentNode && node.parentNode.nodeName === 'LI';
              },
              replacement: function (content) {
                return content; // Return content directly without extra paragraph newlines
              }
            });
            
            // Refined rule for task list items
            turndownService.addRule('taskListItems', {
              filter: function (node) {
                // More specific filter: LI that directly contains an INPUT checkbox,
                // or LI whose first child P directly contains an INPUT checkbox.
                if (node.nodeName !== 'LI') return false;
                if (node.classList.contains('task-list-item')) return true; // If it has the class, assume it's a task item.
                
                const firstChild = node.firstChild;
                if (firstChild && firstChild.nodeName === 'INPUT' && firstChild.type === 'checkbox') {
                  return true; // e.g. <li><input type="checkbox"> Text</li>
                }
                if (firstChild && firstChild.nodeName === 'P' && 
                    firstChild.firstChild && firstChild.firstChild.nodeName === 'INPUT' && 
                    firstChild.firstChild.type === 'checkbox') {
                  return true; // e.g. <li><p><input type="checkbox"> Text</p></li>
                }
                return false;
              },
              replacement: function (content, node) {
                const inputElement = node.querySelector('input[type="checkbox"]');
                const checked = inputElement ? inputElement.checked : false;
                
                // 'content' is what Turndown has processed for the children of the <li>.
                // This should be the text label of the task item.
                // We need to remove any leading list markers if Turndown added them.
                let text = content.trim().replace(/^[-*]\s*\[[ x]\]\s*/, '').replace(/^[-*]\s*/, '').trim();
                console.log(`popup.js: TaskListItem content IN: "${content}", processed text OUT: "${text}"`);

                // Construct the GFM task list item.
                // Construct the GFM task list item.
                // The newline is important here for separation.
                return (checked ? '- [x] ' : '- [ ] ') + text + '\n'; 
              }
            });
            
            // The default 'li' rule in Turndown will add its own bullet and newline.
            // We want our taskListItems rule to completely replace the li handling for task items.
            // The order of rules matters. Custom rules are typically checked before built-in ones.
            // By returning a string ending in \n from our rule, we take control of the line.
            // The final turndown() call might trim the very last newline of the whole document.
            
            // Ensure list items (li) themselves produce a newline, and their content is processed.
            // Turndown's default 'li' rule usually does this, but we can be explicit if needed.
            // This rule might conflict if the default is already good.
            // turndownService.addRule('listItem', {
            //   filter: 'li',
            //   replacement: function (content, node, options) {
            //     content = content.replace(/^\\s+/, '').replace(/\\s+$/, ''); // Trim leading/trailing whitespace from content
            //     let prefix = options.bulletListMarker + ' ';
            //     // If it's a task list item, our specific rule above should have handled it.
            //     // This is for regular list items.
            //     if (node.parentNode.nodeName === 'OL') {
            //       // This part is tricky for ordered lists without knowing the start number.
            //       // For simplicity, let's assume Turndown handles OL numbering.
            //       // If not, one would need to track list item index.
            //       prefix = (node.parentNode.getAttribute('start') ? Number(node.parentNode.getAttribute('start')) : 1) + Array.from(node.parentNode.children).indexOf(node) + '. ';
            //     }
            //     return prefix + content + (node.nextSibling ? '\\n' : '');
            //   }
            // });


            markdownText = turndownService.turndown(chatGPT_HTML_Response);
            statusP.textContent = 'Converted to Markdown. Preparing download...';
          } catch (e) {
            console.error("Error during Turndown conversion:", e);
            statusP.textContent = 'Markdown conversion error.';
            markdownText = `Error during Markdown conversion: ${e.message}\\n\\nOriginal HTML:\\n${chatGPT_HTML_Response}`;
          }
        } else {
          console.error("TurndownService is not defined. Ensure turndown.js is loaded.");
          statusP.textContent = 'Turndown library not found.';
          markdownText = `Turndown library not loaded. Original HTML:\\n${chatGPT_HTML_Response}`;
        }
        
        // Send data to background script for download
        chrome.runtime.sendMessage({
          action: "downloadMarkdown", // New action name
          filename: topicName,
          chatGPTText: markdownText // Send the converted Markdown text
        }, (response) => {
          if (chrome.runtime.lastError) {
            statusP.textContent = 'Error sending to background.';
            console.error('Error sending message to background:', chrome.runtime.lastError.message);
            saveButton.disabled = false;
          } else if (response && response.status === "success") {
            statusP.textContent = `Download started! (ID: ${response.downloadId || 'N/A'})`;
            setTimeout(() => window.close(), 1500); // Close popup after a delay
          } else if (response && response.status === "success_no_id") {
            statusP.textContent = 'Download initiated (no ID returned).';
            setTimeout(() => window.close(), 1500);
          } else if (response && response.status === "cancelled") {
            statusP.textContent = 'Download cancelled by user.';
            saveButton.disabled = false;
          } else {
            statusP.textContent = `Download failed: ${response ? response.error : 'Unknown error'}`;
            saveButton.disabled = false;
          }
        });
      } else {
        statusP.textContent = 'Failed to get text from page.';
        console.error('content.js did not return expected result. Result:', results);
        saveButton.disabled = false;
      }
    } catch (e) {
      statusP.textContent = 'An error occurred.';
      console.error('Error in popup.js:', e);
      saveButton.disabled = false;
    }
  });
});
