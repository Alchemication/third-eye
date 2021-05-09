(() => {
    'use strict';

    /**
     * Keep fetching last heart beat timestamp, and update DOM element
     * @returns {array}
     */
    const startHeartBeatTimer = async (heartBeatContainer) => {
        const response = await fetch(`/heart-beat`);
        if (response.status === 200) {
            // read Json response
            const responseJson = await response.json();
            // update DOM, show heart or umbrella, depending if health is ok
            const heartBeatHealth = responseJson.is_ok ? '❤' : '☂';
            heartBeatContainer.innerText = `${heartBeatHealth} ${new Date(responseJson.hb.create_ts)}`;
        } else {
            // @TODO: Handle errors more gracefully here
            console.error('**ERROR**', response.status, response.statusText);
            window.alert(`ERROR. Code: ${response.status}, msg: ${response.statusText}`)
        }
        // run again itself in 30 seconds
        setTimeout(() => {
            startHeartBeatTimer(heartBeatContainer)
        }, 30000);
    };

    /**
     * Fetch analysis details
     * @param {string} analysisType [motion, objects]
     * @returns {array}
     */
    const fetchAnalysis = async (analysisType) => {
        const response = await fetch(`/analysis?at=${analysisType}`);
        if (response.status === 200) {
            return await response.json();
        } else {
            // @TODO: Handle errors more gracefully here
            console.error('**ERROR**', response.status, response.statusText);
            window.alert(`ERROR. Code: ${response.status}, msg: ${response.statusText}`)
            return null;
        }
    };

    /**
     * Render Plotly line graph for a list of objects
     * @param {array} results
     * @param {string} type
     * @param {object} targetEl
     */
    const renderPlot = (results, type, targetEl) => {
        // extract properties from objects
        const x = [];
        const hist = [];
        const today = [];
        results.forEach(el => {
            x.push(`${el.Hour}:00`);
            hist.push(el.Historical);
            today.push(el.Today);
        });
        // define traces
        const traceHist = {
            name: 'Last 6 Days avg',
            x: x,
            y: hist,
            mode: 'lines+markers',
            type: 'scatter',
            line: {color: '#666'}
        }
        const traceToday = {
            name: 'Today',
            x: x,
            y: today,
            mode: 'lines+markers',
            type: 'scatter',
            line: {color: '#18a2b8'}
        }
        // configure layout
        const layout = {
            autosize: true,
            title: {
                text: `Today's Detections vs 6 days avg`,
                font: {color: '#DDD'},
            },
            margin: {
                t: 50,
                b: 50,
                l: 25,
                r: 15,
                pad: 0
            },
            // showlegend: false, // turn off legend
            legend: {
                font: {color: '#DDD'},
                // orientation: "h" // better for mobiles,
                x: 0.5,
                xanchor: 'right',
                y: 0.985
            },
            xaxis: {
                // title: 'Hour',
                titlefont: {color: '#DDD'},
                tickfont: {color: '#999'}
            },
            yaxis: {
                // title: 'Detections Count',
                standoff: 0,
                titlefont: {color: '#DDD'},
                tickfont: {color: '#999'},
            },
            plot_bgcolor:"#212529",
            paper_bgcolor: "#212529"
        };
        // additional config
        const config = {
            responsive: true,
            displayModeBar: false // never show the top bar with Plotly options (it's kinda redundant)
        };
        // render plot
        Plotly.newPlot(targetEl, [traceHist, traceToday], layout, config);
    };

    const showSpinner = spinnerMsg => {
        spinner.style.display = 'inline-flex';
        eye.classList.add('rotating');
    };

    const hideSpinner = () => {
        spinner.style.display = 'none';
        eye.classList.remove('rotating');
    };

    // show correct content section based on the user's selection
    const displayContent = async idx => {
        if (idx === 0) {
            // show video stream, remove other sections
            hideSpinner();
            videoStream.style.display = 'grid';
            motionAnalysis.style.display = 'none';
            objectsAnalysis.style.display = 'none';
            forensics.style.display = 'none';
            btnVideoStream.classList.add('active');
            btnMotionAnalysis.classList.remove('active');
            btnObjectsAnalysis.classList.remove('active');
            btnForensics.classList.remove('active');
        } else if (idx === 1) {
            // show motion analysis & remove other sections
            hideSpinner();
            videoStream.style.display = 'none';
            motionAnalysis.style.display = 'grid';
            objectsAnalysis.style.display = 'none';
            forensics.style.display = 'none';
            btnVideoStream.classList.remove('active');
            btnMotionAnalysis.classList.add('active');
            btnObjectsAnalysis.classList.remove('active');
            btnForensics.classList.remove('active');
            // fetch latest motion analysis data
            showSpinner('Fetching results...');
            const results = await fetchAnalysis('motion');
            // render plotly graph
            if (results) {
                renderPlot(results, 'Motion', motionAnalysis);
            }
            hideSpinner();
        } else if (idx === 2) {
            // show objects analysis & remove other sections
            hideSpinner();
            videoStream.style.display = 'none';
            motionAnalysis.style.display = 'none';
            objectsAnalysis.style.display = 'grid';
            forensics.style.display = 'none';
            btnVideoStream.classList.remove('active');
            btnMotionAnalysis.classList.remove('active');
            btnObjectsAnalysis.classList.add('active');
            btnForensics.classList.remove('active');
            // fetch latest objects analysis data
            showSpinner('Fetching results...');
            const results = await fetchAnalysis('objects');
            // render plotly graph
            if (results) {
                renderPlot(results['person'], '[Person] Object', objectsAnalysis);
            }
            hideSpinner();
        } else if (idx === 3) {
            // show objects analysis & remove other sections
            hideSpinner();
            videoStream.style.display = 'none';
            motionAnalysis.style.display = 'none';
            objectsAnalysis.style.display = 'none';
            forensics.style.display = 'grid';
            btnVideoStream.classList.remove('active');
            btnMotionAnalysis.classList.remove('active');
            btnObjectsAnalysis.classList.remove('active');
            btnForensics.classList.add('active');
            // fetch latest objects analysis data
            showSpinner('Fetching results...');
            console.log('Forensics');
            // fetch config data to set the gallery
            // hideSpinner();
        } else {
            throw new Error('Undefined element index reached');
        }
    };

    // define DOM elements to manipulate in the process
    const contentContainer = document.querySelector('#content-container');
    const videoStream = document.querySelector('#video-stream');
    const motionAnalysis = document.querySelector('#motion-analysis');
    const objectsAnalysis = document.querySelector('#objects-analysis');
    const btnVideoStream = document.querySelector('#btn-video-stream');
    const btnMotionAnalysis = document.querySelector('#btn-motion-analysis');
    const btnObjectsAnalysis = document.querySelector('#btn-objects-analysis');
    const forensics = document.querySelector('#forensics');
    const btnForensics = document.querySelector('#btn-forensics');
    const heartBeat = document.querySelector('#last-heart-beat-time');
    const spinner = document.querySelector('#spinner');
    const eye = document.querySelector('#eye');

    // use to emulate touch events in the browser
    TouchEmulator();

    // set up a timer to poll for last heart beat every N-seconds
    startHeartBeatTimer(heartBeat);

    // keep track of the selected content (start on Video-Feed, i.e. index=0)
    // TODO: read initial index from URL
    let contentIdx = 0;

    // add tap event to the top buttons,
    // display appropriate content based on the selection
    new Hammer(btnVideoStream).on('tap', ev => {
        contentIdx = 0;
        displayContent(contentIdx);
    });
    new Hammer(btnMotionAnalysis).on('tap', ev => {
        contentIdx = 1;
        displayContent(contentIdx);
    });
    new Hammer(btnObjectsAnalysis).on('tap', ev => {
        contentIdx = 2;
        displayContent(contentIdx);
    });
    new Hammer(btnForensics).on('tap', ev => {
        contentIdx = 3;
        displayContent(contentIdx);
    });

    // set up swipe left/right events on the content
    new Hammer(contentContainer).on('swipeleft swiperight', ev => {
        switch (ev.type) {
            case 'swiperight':
                // return early if we've swiped to the far left
                if (contentIdx === 0) {
                    return;
                }
                // decrement content index (as we are moving left)
                contentIdx -= 1;
                break;
            case 'swipeleft':
                // return early if we've swiped to the far right
                if (contentIdx === 3) {
                    return;
                }
                // increment content index (as we are moving right)
                contentIdx += 1;
                break;
            default:
                break;
        }
        // render appropriate element, based on the content index
        displayContent(contentIdx);
    });
})();