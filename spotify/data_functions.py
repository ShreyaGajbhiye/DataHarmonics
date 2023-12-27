import pandas as pd
import os


def offset_api_limit(sp, sp_call):
    """
    Get all (non-limited) artists/tracks from a Spotify API call.
    :param sp: Spotify OAuth
    :param sp_call: API function all
    :return: list of artists/tracks
    """
    results = sp_call
    if 'items' not in results.keys():
        results = results['artists']
    data = results['items']
    while results['next']:
        results = sp.next(results)
        if 'items' not in results.keys():
            results = results['artists']
        data.extend(results['items'])
    return data


def get_artists_df(artists):
    """
    Transform and tidy Spotify artist data
    :param artists: list of Spotify artist data
    :return: formatted pandas dataframe
    """
    artists_df = pd.DataFrame(artists)
    artists_df['followers'] = artists_df['followers'].apply(lambda x: x['total'])
    return artists_df[['id', 'uri', 'type', 'name', 'genres', 'followers']]


def get_tracks_df(tracks):
    """
    Transform and tidy Spotify track data
    :param tracks: list of Spotify track data
    :return: formatted pandas dataframe
    """
    tracks_df = pd.DataFrame(tracks)
    # Spread track values if not yet spread to columns
    if 'track' in tracks_df.columns.tolist():
        tracks_df = pd.concat([tracks_df.drop('track', axis=1), tracks_df['track'].apply(pd.Series)], axis=1)
        #tracks_df = tracks_df.drop('track', axis=1).assign(**tracks_df['track'].apply(pd.Series))
    # Album
    tracks_df['album_id'] = tracks_df['album'].apply(lambda x: x['id'] if isinstance(x, dict) else None)
    tracks_df['album_name'] = tracks_df['album'].apply(lambda x: x['name'] if isinstance(x, dict) else None)
    tracks_df['album_release_date'] = tracks_df['album'].apply(lambda x: x['release_date'] if isinstance(x, dict) else None)
    tracks_df['album_tracks'] = tracks_df['album'].apply(lambda x: x['total_tracks'] if isinstance(x, dict) else None)
    tracks_df['album_type'] = tracks_df['album'].apply(lambda x: x['type'] if isinstance(x, dict) else None)
    # Album Artist
    def extract_album_artist_id(x):
        if isinstance(x, dict) and 'artists' in x and len(x['artists']) > 0:
            return x['artists'][0]['id']
        return None
    tracks_df['album_artist_id'] = tracks_df['album'].apply(extract_album_artist_id)
    def extract_album_artist_name(x):
        if isinstance(x, dict) and 'artists' in x and len(x['artists']) > 0:
            return x['artists'][0]['name']
        return None

    tracks_df['album_artist_name'] = tracks_df['album'].apply(extract_album_artist_name)
    # Artist
    def extract_artist_id(x):
        if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'id' in x[0]:
            return x[0]['id']
        return None

    def extract_artist_name(x):
        if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'name' in x[0]:
            return x[0]['name']
        return None

    tracks_df['artist_id'] = tracks_df['artists'].apply(extract_artist_id)
    tracks_df['artist_name'] = tracks_df['artists'].apply(extract_artist_name)
    select_columns = ['id', 'name', 'popularity', 'type', 'is_local', 'explicit', 'duration_ms', 'disc_number',
                      'track_number',
                      'artist_id', 'artist_name', 'album_artist_id', 'album_artist_name',
                      'album_id', 'album_name', 'album_release_date', 'album_tracks', 'album_type']
    # saved_tracks has ['added_at', 'tracks']
    if 'added_at' in tracks_df.columns.tolist():
        select_columns.append('added_at')
    return tracks_df[select_columns]


def get_track_audio_df(sp, df):
    """
    Include Spotify audio features and analysis in track data.
    :param sp: Spotify OAuth
    :param df: pandas dataframe of Spotify track data
    :return: formatted pandas dataframe
    """
    df = df.copy()
    df = df[df['artist_id'].notna()]
    df['genres'] = df['artist_id'].apply(lambda x: sp.artist(x)['genres'])
    df['album_genres'] = df['album_artist_id'].apply(lambda x: sp.artist(x)['genres'])
    audio_features = df['id'].apply(lambda x: sp.audio_features(x))
    audio_features_df = pd.DataFrame(audio_features.tolist())
    # Concatenate audio features with the original DataFrame
    df = pd.concat([df, audio_features_df], axis=1)
    # Drop the original 'audio_features' column
    #df = df.drop('audio_features', axis=1)


    # Audio features
    #df['audio_features'] = df['id'].apply(lambda x: sp.audio_features(x))


    #df['audio_features'] = df['audio_features'].apply(pd.Series)
    #df = df.drop('audio_features', 1).assign(**df['audio_features'].apply(pd.Series))
    # Don't need sp.audio_analysis(track_id) audio analysis for this project
    return df


def get_all_playlist_tracks_df(sp, sp_call):
    """
    Get all (non-limited) tracks from a Spotify playlist API call
    :param sp:
    :param sp_call:
    :param sp: Spotify OAuth
    :param sp_call: API function all
    :return: list of tracks
    """
    playlists = sp_call
    playlist_data, data = playlists['items'], []
    playlist_ids, playlist_names, playlist_tracks = [], [], []
    # Uncomment this to pull every single saved playlist (commented out here to no blow up data size)
    while playlists['next']:
         playlist_results = sp.next(playlists)
         playlist_data.extend(playlist_results['items'])
    for playlist in playlist_data:
        saved_tracks = sp.playlist(playlist['id'], fields="tracks, next")
        results = saved_tracks['tracks']
        for item in results['items']:
            data.append(item)
            playlist_ids.append(playlist['id'])
            playlist_names.append(playlist['name'])
            playlist_tracks.append(playlist['tracks']['total'])
        while results['next']:
            results = sp.next(results)
            for item in results['items']:
                data.append(item)
                playlist_ids.append(playlist['id'])
                playlist_names.append(playlist['name'])
                playlist_tracks.append(playlist['tracks']['total'])


    tracks_df = pd.DataFrame(data)
    print(len(playlist_ids))
    print(len(tracks_df))
    # Playlists
    tracks_df['playlist_id'] = playlist_ids
    tracks_df['playlist_name'] = playlist_names
    tracks_df['playlist_tracks'] = playlist_tracks
    # Dataframe manipulation
    tracks_df = tracks_df[tracks_df['is_local'] == False]  # remove local tracks (no audio data)
    tracks_df = tracks_df.drop('track', axis=1).assign(**tracks_df['track'].apply(pd.Series))
    # Album
    tracks_df['album_id'] = tracks_df['album'].apply(lambda x: x['id'] if isinstance(x, dict) else None)
    tracks_df['album_name'] = tracks_df['album'].apply(lambda x: x['name'] if isinstance(x, dict) else None)
    tracks_df['album_release_date'] = tracks_df['album'].apply(lambda x: x['release_date'] if isinstance(x, dict) else None)
    tracks_df['album_tracks'] = tracks_df['album'].apply(lambda x: x['total_tracks'] if isinstance(x, dict) else None)
    tracks_df['album_type'] = tracks_df['album'].apply(lambda x: x['type'] if isinstance(x, dict) else None)
    # Album Artist
    def extract_album_artist_id(x):
        if isinstance(x, dict) and 'artists' in x and len(x['artists']) > 0:
            return x['artists'][0]['id']
        return None
    tracks_df['album_artist_id'] = tracks_df['album'].apply(extract_album_artist_id)
    def extract_album_artist_name(x):
        if isinstance(x, dict) and 'artists' in x and len(x['artists']) > 0:
            return x['artists'][0]['name']
        return None

    tracks_df['album_artist_name'] = tracks_df['album'].apply(extract_album_artist_name)
    # Artist
    def extract_artist_id(x):
        if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'id' in x[0]:
            return x[0]['id']
        return None

    def extract_artist_name(x):
        if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'name' in x[0]:
            return x[0]['name']
        return None

    tracks_df['artist_id'] = tracks_df['artists'].apply(extract_artist_id)
    tracks_df['artist_name'] = tracks_df['artists'].apply(extract_artist_name)
    # playlist_tracks has ['added_at', 'added_by', 'is_local', 'primary_color', 'track', 'video_thumbnail']
    select_columns = ['id', 'name', 'popularity', 'type', 'is_local', 'explicit', 'duration_ms', 'disc_number',
                      'track_number',
                      'artist_id', 'artist_name', 'album_artist_id', 'album_artist_name',
                      'album_id', 'album_name', 'album_release_date', 'album_tracks', 'album_type',
                      'playlist_id', 'playlist_name', 'playlist_tracks',
                      'added_at', 'added_by']
    return tracks_df[select_columns]


def get_recommendations(sp, tracks):
    """
    Get recommendations from a list of Spotify track ids.
    :param sp: Spotify OAuth
    :param tracks: list of Spotify track ids
    :return: list of tracks
    """
    data = []
    for x in tracks:
        results = sp.recommendations(seed_tracks=[x])  # default api limit of 20 is enough
        data.extend(results['tracks'])
    return data
