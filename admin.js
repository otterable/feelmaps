document.getElementById('deleteAllPins').addEventListener('click', function() {
    fetch('/delete_all_pins', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => alert(data.message));
});

document.getElementById('deleteSelectedPins').addEventListener('click', function() {
    // Logic to get selected pin IDs. For simplicity, let's assume you have them in a list:
    const selectedPinIds = [1, 2, 3];  // Replace this with actual logic

    fetch('/delete_selected_pins', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            selected_ids: selectedPinIds
        })
    })
    .then(response => response.json())
    .then(data => alert(data.message));
});

document.getElementById('deleteAllPins').addEventListener('click', function() {
    fetch('/delete_all_pins', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        removeAllPins();
    });
});

document.getElementById('deleteSelectedPins').addEventListener('click', function() {
    // Logic to get selected pin IDs. For simplicity, let's assume you have them in a list:
    const selectedPinIds = [1, 2, 3];  // Replace this with actual logic

    fetch('/delete_selected_pins', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            selected_ids: selectedPinIds
        })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        removeSelectedPins(selectedPinIds);
    });
});
