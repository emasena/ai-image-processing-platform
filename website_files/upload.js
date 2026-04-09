document.getElementById('imageUpload').addEventListener('change', function(e) {
  const fileName = e.target.files[0].name;
  document.querySelector('.custom-file-label').textContent = fileName;
});

document.getElementById('upload-form').addEventListener('submit', function(e) {
  e.preventDefault();

  // Show spinner
  document.getElementById('spinner').style.display = 'block';

  // Get the file to upload
  const file = document.getElementById('imageUpload').files[0];
  if (!file) {
      alert('Please select a file to upload.');
      return;
  }

  // Fetch the pre-signed URL from the Lambda function
  const contentType = file.type; 
  fetch(`https://ex7a6l73rg6jynrfqtcpof5tue0pisuf.lambda-url.us-east-1.on.aws/generate-presigned-url?content-type=${encodeURIComponent(contentType)}`) // FUNCTION URL PLACEHOLDER
      .then(response => response.json())
      .then(data => {
          const uploadUrl = data.upload_url;

          // Use the pre-signed URL to upload the file to S3
          fetch(uploadUrl, {
              method: 'PUT',
              headers: {
                  'Content-Type': contentType
              },
              body: file
          })
          .then(uploadResponse => {
              if (uploadResponse.ok) {
                  // Hide spinner
                  document.getElementById('spinner').style.display = 'none';

                  // Show success message
                  document.getElementById('message').innerHTML = `<div class="alert alert-success" role="alert">File "${file.name}" successfully uploaded.</div>`;

                  // Reset form and label
                  document.getElementById('upload-form').reset();
                  document.querySelector('.custom-file-label').textContent = 'Choose file';
              } else {
                  throw new Error('Upload failed');
              }
          })
          .catch(error => {
              console.error('Error uploading file:', error);
              // Hide spinner
              document.getElementById('spinner').style.display = 'none';

              // Show error message
              document.getElementById('message').innerHTML = `<div class="alert alert-danger" role="alert">Error uploading file.</div>`;
          });
      })
      .catch(error => {
          console.error('Error fetching pre-signed URL:', error);
          // Hide spinner
          document.getElementById('spinner').style.display = 'none';

          // Show error message
          document.getElementById('message').innerHTML = `<div class="alert alert-danger" role="alert">Error fetching pre-signed URL.</div>`;
      });
});
