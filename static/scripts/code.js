// Click event for loading spinners
document.getElementById("newGames").onclick = function() {
    document.getElementById("loadingSpinner").style.visibility = "visible";
    document.getElementById("loadingSpinner").style.display = "block";
}

document.getElementById("submit").onclick = function() {
    document.getElementById("loadingSpinnerDiscover").style.visibility = "visible";
    document.getElementById("loadingSpinnerDiscover").style.display = "block";
}

// Click events to handle the display of the discovery form
document.getElementById("discoverBtn").onclick = function() {
    if (document.getElementById("discoverSection").style.display == "none") {
        document.getElementById("discoverSection").style.visibility = "visible";
        document.getElementById("discoverSection").style.display = "block";

        document.getElementById("discoverBtn").innerHTML = "Close"
    }
    else {
        document.getElementById("discoverSection").style.visibility = "hidden";
        document.getElementById("discoverSection").style.display = "none";

        // Reset the choices selected on the form when a user closes it and set button name back
        document.getElementById("discovery").reset()
        document.getElementById("discoverBtn").innerHTML = "Discover"
    }
}
//