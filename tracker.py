import sqlite3, psutil, time,requests, re,sys
from urllib.parse import quote
from guessit import guessit

# Media Players
MPC = 'mpc-hc64.exe'
file_types = ['avi','mkv','mp4','wmv']

video_name = ""
video_season = ""
video_episode = ""
media_type = ""
video_year = ""

path = 'ENTER YOUR PATH TO DB FILE'
conn = sqlite3.connect(path)
c = conn.cursor()

TAG_RE = re.compile(r'<[^>]+>')


def thingy_capitalize(sentence):
    articles = ['a', 'an', 'of', 'the', 'is']
    result = []
    for word in sentence.split(' '):
        if word in articles:
            result.append(word)
        else:
            result.append(word[0].upper() + word[1:])
    return ' '.join(result)


def remove_tags(text):
    return TAG_RE.sub('', text)


def create_table():
    c.execute('''CREATE TABLE IF NOT EXISTS shows_series(show TEXT, premiered TEXT, year INTEGER, genre TEXT, completed INTEGER, dropped INTEGER, season INTEGER,
episode INTEGER, onhold INTEGER, priority INTEGER, type TEXT, rating INTEGER, status TEXT, country TEXT, avgRating INTEGER, days TEXT, image TEXT, summary TEXT,
time TEXT, nextepiairdate TEXT, nextepiairstamp TEXT, nextepinumber INTEGER, nextepiseason INTEGER, network TEXT, runtime INTEGER, imdb TEXT, thetvdb TEXT,
tvrage TEXT, nextepiname TEXT, nextepisummary TEXT)''')


def add_entry(title, episode, season, type):
    print("Not Found in DB. Now adding show: [" + str(title) + "]")
    if type == 'episode':
        type = 'TV'
    c.execute("INSERT INTO shows_series (show, episode, season, type) VALUES (?, ?, ?, ?)", (title, episode, season, type))
    conn.commit()
    grab_show_meta(title)


def update_del(name, episode, season, type):
    print("[ " + name + " ]Season: " + str(season)+" episode: " + str(episode))
    x = c.execute('''SELECT season, episode, type FROM shows_series WHERE show=?''',(name,))
    y = x.fetchmany(2)[0]
    seas = y[0]
    epi = y[1]
    type = y[2]

    if type == 'TV':
        if season > seas:
            c.execute('''UPDATE shows_series SET season =?, episode = ?, type = ? WHERE show=?''',
                      (season, episode, "TV", name))
            conn.commit()
            print("Show updated.")
        elif season == seas:
            if episode >= epi:
                c.execute('''UPDATE shows_series SET season =?, episode = ?, type = ? WHERE show=?''',
                          (season, episode, "TV", name))
                conn.commit()
                print("Show updated.")
            else:
                print("watching older episode. Not updating.")

        else:
            print("watching older episode. Not updating.")


def checker_entry(name, episode, season, type):
    c.execute('SELECT 1 FROM shows_series WHERE show = ?', (name,))
    print("Checking Database for [" + str(name) + "]")
    if c.fetchone():
        print("Updating Episode...")
        update_del(name, episode, season, type)

    else:
        add_entry(name, episode, season, type)
        conn.commit()


def grab_show_meta(name):
    print("Now adding show meta")
    c.execute('SELECT 1 FROM shows_series WHERE show = ? ', (name,))
    if c.fetchone():
        print("Show [" + str(name) + "] found in database. Updating Meta.")
        qstr = quote(name)
        json_data = requests.get("http://api.tvmaze.com/singlesearch/shows?q=" + qstr).json()

        video_genre = json_data['genres']
        show_status = json_data['status']
        show_runtime = json_data['runtime']
        show_premiered = json_data['premiered']
        show_schedule = json_data['schedule']
        show_rating = json_data['rating']
        show_image = json_data['image']
        show_summary = json_data['summary']
        show_air_time = show_schedule['time']
        show_air_day = show_schedule['days']
        iMDB = json_data['externals']['imdb']
        thetvdb = json_data['externals']['thetvdb']
        tvrage = json_data['externals']['tvrage']

        next_epi_airstamp = ""
        next_epi_number = ""
        next_epi_season = ""
        next_epi_name = ""
        next_epi_summary = ""
        next_epi_airdate = ""
        epi_summary = ""

        temp_summary = remove_tags(show_summary)

        try:
            show_country = json_data['network']['country']['code']
        except TypeError:
            print("No Country Found.")
            show_country = "N/A"

        try:
            show_network = json_data['network']['name']
        except TypeError:
            print("No Show Network Found.")
            show_network = "N/A"

        nextepi = ""
        try:
            nextepi = json_data['_links']['nextepisode']['href']
            epi_data = requests.get(nextepi).json()

            if nextepi:
                print("yes")
                next_epi_name = epi_data['name']
                next_epi_season = epi_data['season']
                next_epi_number = epi_data['number']
                next_epi_airdate = epi_data['airdate']
                next_epi_airstamp = epi_data['airstamp']
                if epi_data['summary']:
                    next_epi_summary = epi_data['summary']
                else:
                    print("No next episode summary")
                print(next_epi_name)
                print(next_epi_number)
                print(next_epi_season)
                print(next_epi_airstamp)
                print(next_epi_summary)
                print(next_epi_airdate)
                epi_summary = remove_tags(next_epi_summary)

            else:
                print("no")

        except KeyError:
            print("No details for next episode found")

        new_genre = ", ".join(video_genre)
        new_air_date = ", ".join(show_air_day)

        c.execute('''UPDATE shows_series SET status =?, time = ?, avgRating = ?, days = ?, country = ?, genre = ?, image = ?, summary = ?, network = ?, runtime = ?, premiered = ?, imdb = ?, thetvdb = ?, tvrage = ?,
 nextepiairstamp = ?, nextepiairdate = ?,nextepinumber = ?,nextepiseason = ?, nextepiname = ?, nextepisummary = ? WHERE show=?''',
                  (show_status, show_air_time, show_rating['average'], new_air_date, show_country, new_genre, show_image['medium'], temp_summary, show_network, show_runtime, str(show_premiered), str(iMDB), str(thetvdb), str(tvrage),
                   next_epi_airstamp, next_epi_airdate,next_epi_number,next_epi_season, next_epi_name,epi_summary, name))
        conn.commit()


# Update show meta if series is not Ended
def fetch():
    c.execute("SELECT show, status, type FROM shows_series")
    for row in c.fetchall():
        if row[2] == 'TV':
            if row[1] != 'Ended':
                grab_show_meta(str(row[0]))
            else:
                print("Show has ended. No meta updated.")


def countdown(t): # in seconds
    for i in range(t,0,-1):
        # print("\r"+'tasks done, now sleeping for %d seconds' % i)
        # print(time.ctime(), end="\r", flush=True)

        time.sleep(1)
        sys.stdout.write(str(i) + ' ')
        sys.stdout.flush()


def tracking():
    while True:
        for proc in psutil.process_iter():

                if proc.name() == MPC:
                    opened_files = proc.open_files()
                    for files in opened_files:
                        for items in file_types:
                            if files[0].endswith(items):
                                test = guessit(files[0])
                                print(test)

                                video_season = test.get('season')
                                video_episode = test.get('episode')
                                media_type = test.get('type')

                                video_name = thingy_capitalize(test.get('title'))

                                print("Now playing: [" + str(video_name) + "]" )

                                checker_entry(video_name, video_episode, video_season, media_type)
                                countdown(10)
                else:
                    print("No video player open. Now sleeping: ")
                    countdown(20)



def edit_entry():
    print("Entry title of the entry you want to change.")
    user_input = thingy_capitalize(input(">"))
    title = user_input

    c.execute('SELECT 1 FROM shows_series WHERE show = ?', (user_input,))
    print("Checking Database for [" + str(user_input) + "]")
    if c.fetchone():

        while True:
            print("Title found.")
            print("")
            print('Select an Option:')
            print('(1) Set as "Watching"')
            print('(2) Set as "Dropped"')
            print('(3) Set as "On-Hold"')
            print('(4) Set as "Completed"')
            print('(5) Set as "Priority"')
            print('(6) Set Rating')
            print('(7) Edit Episode/Season #')
            print('(8) Exit')

            user_input = input('>')

            if user_input == '1':
                c.execute('''UPDATE shows_series SET dropped = ?, onhold = ? WHERE show =?''', (0, 0, title))
                conn.commit()
                print("Set as Watching, and removed from 'On-hold'")
            elif user_input == '2':
                c.execute('''UPDATE shows_series SET dropped = ? WHERE show =?''', (1,title))
                conn.commit()
                print("Dropped.")
            elif user_input == '3':
                c.execute('''UPDATE shows_series SET onhold = ? WHERE show =?''', (1, title))
                conn.commit()
                print("Onhold.")
            elif user_input == '4':
                c.execute('''UPDATE shows_series SET completed = ? WHERE show =?''', (1, title))
                conn.commit()
                print("Completed.")
            elif user_input == '5':
                c.execute('''UPDATE shows_series SET priority = ? WHERE show =?''', (1, title))
                conn.commit()
                print("Prioritized.")
            elif user_input == '6':
                print("Set a rating from 1 to 10")
                user_input = int(input('>'))
                c.execute('''UPDATE shows_series SET rating = ? WHERE show =?''', (user_input, title))
                conn.commit()
                print("Rated..")
            elif user_input == '7':
                c.execute('''SELECT episode, season FROM shows_series WHERE show =?''', (title,))
                x = c.fetchone()
                episode = x[0]
                season = x[1]
                print("Current values: season ["+str(season)+"]  episode["+str(episode)+ "] ")
                user_input_episode = int(input('(Set episode #) >'))
                user_input_season = int(input('(Set season  #) >'))
                c.execute('''UPDATE shows_series SET episode = ?, season = ? WHERE show =?''', (user_input_episode, user_input_season, title))
                conn.commit()
                print("Changed Values.")
            elif user_input =='8':
                break;


def mainMenu():
    print('Select an Option:')
    print('(1) Tracking')
    print('(2) Update Meta')
    print('(3) Edit Entry')
    print('(4) Exit')

    user_input = input('>')

    if user_input == '1':
        tracking()
    elif user_input == '2':
        fetch()
    elif user_input == '3':
        edit_entry()
    elif user_input == '4':
        exit()


while True:
    mainMenu()


# create_table()
