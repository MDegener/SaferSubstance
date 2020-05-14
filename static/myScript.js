
// Activate all tooltips
$(document).ready(function(){
    $('[data-toggle="tooltip"]').tooltip();
});

function voteAdvice(vote, adviceID, userID) {

    $(document).ready(function(){

        $.ajax({
            url: "/voteAdvice",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                "user": userID,
                "advice": adviceID,
                "vote": vote
            }),
            success: function(data) {
                changeVoteDisplay(adviceID, vote, data.type)
            }
        });
    });
}

function voteSuggestion(vote, substanceID, userID, substance) {

    $(document).ready(function(){

        $.ajax({
            url: "/voteSuggestion",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                "user": userID,
                "substance": substance,
                "vote": vote
            }),
            success: function(data) {
                changeVoteDisplay(substanceID, vote, data.type)
            }
        });
    });
}

function changeVoteDisplay(id, vote, type) {

    var n = parseInt(document.getElementById(id).innerHTML, 10);

    if (type == "unvote") {
        document.getElementById(id).innerHTML = n - vote;
        document.getElementById("up " + id).style.color = "white";
        document.getElementById("down " + id).style.color = "white";
    }
    else {
        if (type == "new") {
            document.getElementById(id).innerHTML = n + vote;
        }
        else if (type == "change") {
            document.getElementById(id).innerHTML = n + vote * 2;
        }

        if (vote == 1) {
            document.getElementById("up " + id).style.color = "#00bc8c";
            document.getElementById("down " + id).style.color = "white";
        }
        else if (vote == -1) {
            document.getElementById("up " + id).style.color = "white";
            document.getElementById("down " + id).style.color = "#00bc8c";
        }
    }
}