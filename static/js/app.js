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
                
                // Convert Markdown response to HTML
                var converter = new showdown.Converter();
                var html = converter.makeHtml(response.response);

                // Display the response and make it visible
                $('#response').html(html).show();
            },
            error: function (xhr, status, error) {
                $('#loadingSpinner').hide();
                $('#response').html('<h3>Error:</h3><p>' + xhr.responseJSON.error + '</p>').show();
            }
        });
    });
});
