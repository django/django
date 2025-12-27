document.addEventListener('DOMContentLoaded', () => {
    const codeBlocks = document.querySelectorAll('.highlight');

    codeBlocks.forEach(block => {
        // Create the button
        const button = document.createElement('button');
        button.className = 'copy-button';
        button.type = 'button';
        button.innerText = 'Copy';
        button.setAttribute('aria-label', 'Copy code to clipboard');

        // Add click event
        button.addEventListener('click', () => {
            const pre = block.querySelector('pre');

            // Clone the node to strip prompts without changing the UI
            const clone = pre.cloneNode(true);
            clone.querySelectorAll('.gp').forEach(node => node.remove());

            const textToCopy = clone.innerText.trim();

            navigator.clipboard.writeText(textToCopy).then(() => {
                button.innerText = 'Copied!';
                button.classList.add('copied');
                setTimeout(() => {
                    button.innerText = 'Copy';
                    button.classList.remove('copied');
                }, 2000);
            });
        });

        // Append button to the block
        block.style.position = 'relative';
        block.appendChild(button);
    });
});