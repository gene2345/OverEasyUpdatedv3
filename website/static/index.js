function deleteNote(noteID) {
    fetch('/deleteNote', {
        method : 'POST',
        body: JSON.stringify({ noteID : noteID})
    }).then((_res) => { window.location.href = "/"});
}