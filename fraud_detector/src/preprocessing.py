import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def load_train_data():
    logger.info('Loading training data...')

    # Import Train dataset
    train = pd.read_csv('./train_data/train.csv')
    logger.info('Raw train data imported. Shape: %s', train.shape)

    # Add some features
    train = add_features(train)
    logger.info('Train data processed. Shape: %s', train.shape)

    return train


def haversine(lat1, lon1, lat2, lon2):
    rad = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return rad * c


def add_features(df):
    df_ = df.copy()
    df_['haversine'] = haversine(df_['lat'], df_['lon'],
                                 df_['merchant_lat'], df_['merchant_lon'])
    df_["transaction_time"] = pd.to_datetime(df_["transaction_time"])
    df_["year"] = df_["transaction_time"].dt.year
    df_["month"] = df_["transaction_time"].dt.month
    df_["day"] = df_["transaction_time"].dt.day
    df_["hour"] = df_["transaction_time"].dt.hour
    df_["minute"] = df_["transaction_time"].dt.minute
    df_["weekend"] = (df_["transaction_time"].dt.dayofweek > 4).astype(int)
    amount = pd.to_numeric(df_["amount"])
    population = pd.to_numeric(df_["population_city"])
    df_["amount_log"] = np.log1p(amount.clip(lower=0))
    df_["population_log"] = np.log1p(population.clip(lower=0))

    df_["month_sin"] = np.sin(2 * np.pi * df_["month"] / 12)
    df_["month_cos"] = np.cos(2 * np.pi * df_["month"] / 12)

    df_["hour_sin"] = np.sin(2 * np.pi * df_["hour"] / 24)
    df_["hour_cos"] = np.cos(2 * np.pi * df_["hour"] / 24)

    df_["day_sin"] = np.sin(2 * np.pi * df_["day"] / 31)
    df_["day_cos"] = np.cos(2 * np.pi * df_["day"] / 31)

    df_["minute_sin"] = np.sin(2 * np.pi * df_["minute"] / 60)
    df_["minute_cos"] = np.cos(2 * np.pi * df_["minute"] / 60)

    weekday = df_["transaction_time"].dt.dayofweek
    df_["weekday_sin"] = np.sin(2 * np.pi * weekday / 7)
    df_["weekday_cos"] = np.cos(2 * np.pi * weekday / 7)
    df_["night"] = (df_["hour"] < 6).astype(int)
    return df_.drop(columns=["transaction_time", "name_1", "name_2", "street"])


# Main preprocessing function
def run_preproc(input_df):
    # Add features
    output_df = add_features(input_df)
    logger.info('Added new features. Output shape: %s', output_df.shape)

    # Return resulting dataset
    return output_df
