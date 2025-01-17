$(document).ready(function () {
    let currentPrompt = ""; // Store the dynamically selected prompt

    // Button click handlers for dynamic prompts
    $('#btnFinancialPosition').click(function () {
        currentPrompt = `
            You are an AI financial analyst...
            // Include the Financial Position prompt details here
        `;
        $('#btnFinancialPosition').addClass('btn-primary').removeClass('btn-secondary');
        $('.btn-secondary').not(this).removeClass('btn-primary').addClass('btn-secondary');
    });

    // Analyze Button
    $('#analyzeBtn').click(function () {
        const csvFile = $('#csvFile')[0].files[0];
        const borrowerProfile = $('#borrowerProfile')[0].files[0];

        if (!csvFile || !borrowerProfile) {
            alert("Please upload both files before analyzing.");
            return;
        }

        // Show loading bar
        $('#loading').show();

        const formData = new FormData();
        formData.append('csv_file', csvFile);
        formData.append('borrower_profile', borrowerProfile);
        formData.append('prompt', currentPrompt);

        // Send data to backend for analysis
        $.ajax({
            url: '/api/analyze',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                // Format the response text to remove unwanted symbols and add line breaks
                let formattedResponse = formatResponse(response.response);
                $('#response').html(formattedResponse).show();

                // Hide loading bar
                $('#loading').hide();
            },
            error: function (xhr, status, error) {
                alert("Error: " + xhr.responseJSON.error);

                // Hide loading bar if error occurs
                $('#loading').hide();
            }
        });
    });

    // Generate Document Button
    $('#generateDocBtn').click(function () {
        window.location.href = '/api/download';
    });

    // Function to format the response into proper paragraph format
    function formatResponse(responseText) {
        // Remove unwanted symbols like "*" and "#" and extra newlines
        let formattedText = responseText.replace(/[*#]/g, '').trim();

        // Split the text into paragraphs by detecting multiple newlines
        let paragraphs = formattedText.split('\n\n');

        // Join the paragraphs with <p> tags for HTML rendering
        let htmlFormattedResponse = paragraphs.map(paragraph => `<p>${paragraph.trim()}</p>`).join('');
        
        return htmlFormattedResponse;
    }
});
