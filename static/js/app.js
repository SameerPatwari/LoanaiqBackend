$(document).ready(function () {
    $('#uploadForm').on('submit', function (e) {
        e.preventDefault();

        // Show the loading spinner and hide the response section
        $('#loadingSpinner').show();
        $('#response').hide();

        let formData = new FormData(this);

        // Append the default prompt to the form data
        formData.append('prompt', 'summarize this document');

        $.ajax({
            url: '/api/process_pdf',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                // Hide the loading spinner
                $('#loadingSpinner').hide();

                let rawResponse = response.response; // Raw response from the API

                // Preprocess the response to wrap LaTeX formulas correctly
                let processedResponse = rawResponse.replace(
                    /\\\$\$([\s\S]*?)\\\$\$/g, // Match escaped formulas \$$ ... \$$
                    (match, formula) => `$$${formula.trim()}$$` // Replace with valid MathJax formula
                );

                // Convert Markdown to HTML
                var converter = new showdown.Converter({
                    tables: true, // Enable Markdown table support
                });
                var htmlContent = converter.makeHtml(processedResponse);

                // Display the formatted response
                $('#response').html(htmlContent).show();

                // Render MathJax for formulas after content is rendered
                if (window.MathJax) {
                    MathJax.typesetPromise([document.getElementById('response')]).then(function () {
                        console.log("MathJax formulas are rendered");
                    }).catch(function (err) {
                        console.error("MathJax rendering error:", err);
                    });
                }
            },
            error: function (xhr, status, error) {
                $('#loadingSpinner').hide();
                $('#response').html('<h3>Error:</h3><p>' + xhr.responseJSON.error + '</p>').show();
            }
        });
    });
});
