# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import json
import urllib
import urllib2
from xbmc import LOGNOTICE

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))

_debug = False


class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onNotification(self, sender, method, data):
        global susppend_auto_change
        global set_for_susspend

        global anime_playing_file
        global anime_was_played
        global anime_id

        data = json.loads(data)
        if 'System.OnWake' in method:
            pass
        if 'Player.OnStop' in method:
            logger('Player.OnStop', 'METHOD: %s | DATA: %s | FILE: %s' % (str(method), str(data), anime_playing_file))

            try:
                if 'item' in data and 'type' in data['item']:
                    media_type = data['item']['type']
                    watched = data['end']

                    logger('Player.OnStop', '[MONITOR] watched: %s' % str(watched))
                    logger('Player.OnStop', '[MONITOR] Raw data: %s' % str(data))
                    logger('Player.OnStop', '[MONITOR] Media type: %s' % str(media_type))

                    if media_type == 'episode':
                        monitor_paths = []

                        if ',' in ADDON.getSetting('MonitorPaths'):
                            monitor_paths = ADDON.getSetting('MonitorPaths').split(",")
                        else:
                            monitor_paths.append(ADDON.getSetting('MonitorPaths'))

                        for path in monitor_paths:
                            if path.lower() in anime_playing_file:
                                anime_was_played = True

                    logger('Player.OnStop',
                           'Detected Anime and storing for library update event = %s' % anime_was_played)

                    if anime_was_played:
                        anime_id = data['item']['id']
            except:
                logger('Player.OnStop', 'Error occured during MAL scrobble')
                pass

            pass
        if 'Player.OnPlay' in method:
            # logger('Player.OnPlay', '[MONITOR] METHOD: %s | DATA: &s' % (str(method), str(data)))

            try:
                xbmc.sleep(5000)
                anime_playing_file = xbmc.Player().getPlayingFile().lower()
            except:
                pass
            pass
        if 'VideoLibrary.OnUpdate' in method:
            if anime_was_played and anime_id is not 0:
                result = getEpisodeDetailsFromKodi(anime_id, ['showtitle', 'season', 'episode', 'tvshowid',
                                                              'playcount'])

                # Reset so we don't re-use
                anime_was_played = False
                anime_id = 0

                logger('VideoLibrary.OnUpdate', 'Play count: %s' % str(result['playcount']))

                if not result:
                    # logger('Player.OnStop', 'No data was returned from Kodi')
                    pass
                else:
                    if result['playcount'] > 0:
                        updateMALPlaybackStatus(str(result['showtitle']), str(result['episode']), 99)


def getEpisodeDetailsFromKodi(libraryId, fields):
    result = kodiJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails',
                              'params': {'episodeid': libraryId, 'properties': fields}, 'id': 1})
    logger("getEpisodeDetailsFromKodi()", "%s" % str(result))

    if not result:
        logger("getEpisodeDetailsFromKodi()", "Result from Kodi was empty.")
        return None

    show_data = getShowDetailsFromKodi(result['episodedetails']['tvshowid'], ['year', 'imdbnumber'])

    if not show_data:
        logger("getEpisodeDetailsFromKodi()", "Result from getShowDetailsFromKodi() was empty.")
        return None

    result['episodedetails']['imdbnumber'] = show_data['imdbnumber']
    result['episodedetails']['year'] = show_data['year']

    try:
        return result['episodedetails']
    except KeyError:
        logger("getEpisodeDetailsFromKodi()", "KeyError: result['episodedetails']")
        return None


def getShowDetailsFromKodi(showID, fields):
    result = kodiJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails',
                              'params': {'tvshowid': showID, 'properties': fields}, 'id': 1})
    logger("getShowDetailsFromKodi()", "%s" % str(result))

    if not result:
        logger("getShowDetailsFromKodi()", "Result from Kodi was empty.")
        return None

    try:
        return result['tvshowdetails']
    except KeyError:
        logger("getShowDetailsFromKodi()", "KeyError: result['tvshowdetails']")
        return None


def kodiJsonRequest(params):
    data = json.dumps(params)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)
    except UnicodeDecodeError:
        response = json.loads(request.decode('utf-8', 'ignore'))

    try:
        if 'result' in response:
            return response['result']
        return None
    except KeyError:
        logger("kodiJsonRequest", "[%s] %s" % (params['method'], response['error']['message']))
        return None


def updateMALPlaybackStatus(showTitle, showEpisode, percentagePlayed):
    logger('updateMALPlaybackStatus', 'Updating show: %s | Episode: %s | percentage: %s' % (showTitle, showEpisode,
                                                                                            percentagePlayed))
    MALUsername = ADDON.getSetting('MALUsername')
    MALPassword = ADDON.getSetting('MALPassword')

    queryString = {'username': MALUsername, 'password': MALPassword, 'showTitle': showTitle,
                   'showEpisode': str(showEpisode), 'percentagePlayed': str(percentagePlayed)}

    url = 'http://mal-web/api.aspx?' + urllib.urlencode(queryString)
    logger('updateMALPlaybackStatus', 'MAL update url: %s' % url)

    response = urllib2.urlopen(url)
    response.read()


def logger(log_type, log_message, notification=False, force_log=False):
    log_message = 'MAL Scrobbler: {0} | {1}'.format(log_type, log_message)

    if _debug or force_log:
        xbmc.log(log_message, level=LOGNOTICE)
    else:
        xbmc.log(log_message)

    if notification:
        notification_message = 'Notification({0},,5000,'')'.format(log_message)
        xbmc.executebuiltin(notification_message)


monitor = Monitor()

while (not xbmc.abortRequested):
    xbmc.sleep(100)
