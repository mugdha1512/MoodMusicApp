// Camera and Mood Detection
let video = document.getElementById('camera');
let resultDiv = document.getElementById('result');
let captureBtn = document.getElementById('capture');
let quickLogBtn = document.getElementById('quick-log');

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
  }).catch(err => {
    console.error('Camera access denied:', err);
    resultDiv.innerHTML = '<p class="error">Camera access required for mood detection.</p>';
  });
}

captureBtn.addEventListener('click', () => {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const imageData = canvas.toDataURL('image/png');

  fetch('/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageData })
  })
  .then(response => response.json())
  .then(data => {
    displayResult(data);
  })
  .catch(err => {
    console.error('Detection error:', err);
    resultDiv.innerHTML = '<p class="error">Detection failed. Try again!</p>';
  });
});

// Quick Mood Log Modal (Simple dropdown for demo)
quickLogBtn.addEventListener('click', () => {
  const moods = ['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral'];
  let selectedMood = prompt('Select your mood: ' + moods.join(', '));
  if (moods.includes(selectedMood?.toLowerCase())) {
    fetch('/quick_log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ emotion: selectedMood })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        displayResult(data);
        alert('Mood logged! Check your profile.');
      } else {
        alert('Login required for quick log.');
      }
    });
  }
});

function displayResult(data) {
  let html = `<h3>Your Mood: ${data.emotion.toUpperCase()} 😊</h3>`;
  html += '<h4>Recommended Songs:</h4><ul>';
  data.songs.forEach(song => {
    html += `<li><a href="${song.url}" target="_blank">${song.title}</a></li>`;
  });
  html += '</ul>';
  resultDiv.innerHTML = html;
  resultDiv.classList.add('show');
}

// Smooth scroll and animations
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth'
    });
  });
});