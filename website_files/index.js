document.addEventListener('DOMContentLoaded', function() {
  fetch('https://uwdq7v26tsdbuf4k7re74f2twe0dwjzh.lambda-url.us-east-1.on.aws') //Fetch LAMBDA FUNCTION URL - make sure to not add a trailing slash
    .then(response => response.json())
    .then(data => {
      const gallery = document.getElementById('image-gallery');
      data.forEach(image => {
        const card = document.createElement('div');
        card.className = 'card';

        const imgElement = document.createElement('img');
        imgElement.src = image.url;
        imgElement.className = 'card-img-top';
        imgElement.alt = 'Image';
        imgElement.addEventListener('click', () => {
          enlargeImage(image.url);
          document.getElementById('generateDescription').setAttribute('data-image-id', extractImageId(image.url));
        });

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';

        const imgDescription = document.createElement('p');
        imgDescription.className = 'card-text';

        let descriptionText = image.description;
        if (typeof image.description === 'object' && image.description.content && image.description.content.length > 0) {
          descriptionText = image.description.content[0].text;
        }

        imgDescription.textContent = descriptionText;

        cardBody.appendChild(imgDescription);
        card.appendChild(imgElement);
        card.appendChild(cardBody);
        gallery.appendChild(card);
      });
    })
    .catch(error => console.error('Error fetching image data:', error));

  function enlargeImage(src) {
    $('#modalImg').attr('src', src);
    $('#imageModal').modal('show');
  }

  function extractImageId(imageUrl) {
    return imageUrl.substring(imageUrl.lastIndexOf('/') + 1);
  }

  document.getElementById('generateDescription').addEventListener('click', function() {
    const imageId = this.getAttribute('data-image-id');
    console.log('Generating AI description for image ID:', imageId);
    // Show spinner
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    this.disabled = true;
    generateAiDescription(imageId);
  });

  function generateAiDescription(imageId) {
    const aiDescriptionEndpoint = 'https://sx6epnnbyjod7wbjqioslk7cqe0jztpp.lambda-url.us-east-1.on.aws'; // GENERATE AI LAMBDA FUNCTION URL - and 
    fetch(aiDescriptionEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ imageId: imageId }),
    })
    .then(response => response.json())
    .then(data => {
      console.log('AI description generated:', data.description);
      alert('AI Description Generated!');
      document.getElementById('generateDescription').innerHTML = 'Generate AI Description';
      document.getElementById('generateDescription').disabled = false;
    })
    .catch(error => {
      console.error('Error generating AI description:', error);
      document.getElementById('generateDescription').innerHTML = 'Generate AI Description';
      document.getElementById('generateDescription').disabled = false;
    });
  }

  $('#imageModal').on('hidden.bs.modal', function () {
    window.location.reload(); // Refresh page when modal is closed
  });
});
