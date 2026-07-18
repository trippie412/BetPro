import random

REVIEWS = [
    "I honestly thought this was a scam until my first withdrawal arrived.",
    "Deposits are instant and withdrawals are surprisingly fast.",
    "Very clean betting platform. I like the interface.",
    "I have withdrawn twice already. Everything works perfectly.",
    "My first 50,000 from the application thanks to Betpro team",
    "I never Imagined I could Fall for this website Thanks",
    "The odds are competitive and matches update quickly.",
    "Registration took less than a minute.",
    "Customer support replied much faster than I expected.",
    "Won my first accumulator and got paid without any issues.",
    "M-Pesa deposits are very convenient.",
    "The welcome bonus was credited immediately.",
    "Best betting experience I've had so far.",
    "Everything works exactly as advertised.",
    "I was skeptical at first, but BetPro is actually legit.",
    "My friends recommended this platform and I'm impressed.",
    "Simple, fast and trustworthy.",
    "Very secure platform.",
    "The payout process is smooth.",
    "No hidden charges during withdrawal.",
    "I've been using BetPro every day.",
    "Definitely recommending this to my friends."
]

PREFIXES = [
    "0700","0701","0702","0703","0704","0705","0706","0707","0708","0709",
    "0710","0711","0712","0713","0714","0715","0716","0717","0718","0719",
    "0720","0721","0722","0723","0724","0725","0726","0727","0728","0729",
    "0730","0731","0732","0733","0734","0735","0736","0737","0738","0739",
    "0740","0741","0742","0743","0745","0746","0748",
    "0757","0758","0759",
    "0768","0769",
    "0780","0781","0782","0783","0784","0785","0786","0787","0788","0789",
    "0790","0791","0792","0793","0794","0795","0796","0797","0798","0799",
    "0100","0101","0102","0103","0104","0105","0106","0107","0108","0109",
    "0110","0111","0112","0113","0114","0115"
]

def random_phone():
    prefix = random.choice(PREFIXES)
    middle = random.randint(100, 999)
    last = random.randint(10, 99)
    return f"{prefix}*****{last}"

def generate_review():
    return {
        "phone": random_phone(),
        "rating": random.choice([4,5]),
        "review": random.choice(REVIEWS),
        "visible": True
    }