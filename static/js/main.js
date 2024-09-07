// script.js

let signins = 0;
let rank = 'Unranked';
const rankThresholds = {
    'Bronze': 50,
    'Silver': 100,
    'Gold': 200,
    'Platinum': 300
};
const tasks = [
    { id: 1, task: 'Complete the survey', url: 'https://example.com/survey' },
    { id: 2, task: 'Watch the tutorial video', url: 'https://example.com/video' },
];

function handleSignin() {
    signins++;
    rank = calculateRank(signins);
    document.getElementById('output').innerText = `Attendance recorded. You now have ${signins} sign-ins and your rank is '${rank}'.`;
}

function handleReferralLink() {
    const referralLink = `https://t.me/m2e2bot?start=12345`;  // Simulated user ID
    document.getElementById('output').innerText = `Share this referral link with your friends: ${referralLink}`;
}

function handleViewTasks() {
    if (tasks.length > 0) {
        let taskList = 'Here are your active tasks:\n';
        tasks.forEach(task => {
            taskList += `${task.task}: ${task.url}\n`;
        });
        document.getElementById('output').innerText = taskList;
    } else {
        document.getElementById('output').innerText = 'You have no active tasks.';
    }
}

function calculateRank(signins) {
    for (const [key, value] of Object.entries(rankThresholds)) {
        if (signins >= value) {
            return key;
        }
    }
    return 'Unranked';
}
