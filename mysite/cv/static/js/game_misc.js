        var mainSong = new Audio("/static/underworld.mp3");
        var isPlaying = true;
        var playPromise = mainSong.play();
        if (playPromise !== undefined) {
            playPromise.catch(function() {
                isPlaying = false;
            });
        }

        var un_mute = document.getElementById('un-mute');

        un_mute.onclick = function() {
            if(isPlaying){
                mainSong.pause();
                isPlaying = false;
                un_mute.src = "http://upload.wikimedia.org/wikipedia/commons/3/3f/Mute_Icon.svg";
            }
            else{
                mainSong.play();
                isPlaying = true;
                un_mute.src = "http://upload.wikimedia.org/wikipedia/commons/2/21/Speaker_Icon.svg";
            }
        };

        var minutesLabel = document.getElementById("minutes");
        var secondsLabel = document.getElementById("seconds");
        var totalSecondsLabel = document.getElementById("totalSeconds");
        var totalSeconds = 0;
        setInterval(setTime, 1000);

        function setTime()
        {
            ++totalSeconds;
            //secondsLabel.innerHTML = pad(totalSeconds%60);
            //minutesLabel.innerHTML = pad(parseInt(totalSeconds/60));
            totalSecondsLabel.innerHTML = pad(totalSeconds);
        }

        function pad(val)
        {
            var valString = val + "";
            if(valString.length < 2)
            {
                return "0" + valString;
            }
            else
            {
                return valString;
            }
        }
