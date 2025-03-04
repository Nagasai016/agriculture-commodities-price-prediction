from flask import Flask, render_template, request, send_file
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


app = Flask(__name__)


df = pd.read_csv('all_agricultural_products_data.csv')

def train_model(df, target_variable):
    # Select features and target variable
    X = df[['Day', 'Month', 'Year']]
    y = df[target_variable]

    # Split data into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Initialize and train the model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    return model


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_prediction', methods=['POST'])
def select_prediction():
    prediction_type = request.form['prediction_type']
    if prediction_type == 'prices':
        return render_template('predict_prices.html')
    elif prediction_type == 'volumes':
        return render_template('volumes_traded.html')


# Route to handle the form submission and make predictions
@app.route('/predict', methods=['POST'])
def predict():
    # Get inputs from the form
    commodity = request.form['commodity']
    forecast_period = int(request.form['forecast_period'])
    start_date = request.form['start_date']
    target_variable = request.form['target_variable']

    # Filter data for selected commodity
    df_commodity = df[df['commodity'] == commodity]
    df_commodity['date'] = pd.to_datetime(df_commodity['date'])
    df_commodity.sort_values(by='date', inplace=True)
    df_commodity.reset_index(drop=True, inplace=True)

    # Feature engineering: Extracting day, month, and year from Date
    df_commodity['Day'] = df_commodity['date'].dt.day
    df_commodity['Month'] = df_commodity['date'].dt.month
    df_commodity['Year'] = df_commodity['date'].dt.year

    # Train the model
    model = train_model(df_commodity, target_variable)

    # Generate future dates for forecasting
    last_date = datetime.strptime(start_date, '%Y-%m-%d')
    future_dates = pd.date_range(start=last_date, periods=forecast_period, freq='D')

    # Feature engineering for future dates
    future_df = pd.DataFrame({
        'Day': future_dates.day,
        'Month': future_dates.month,
        'Year': future_dates.year
    })

    # Predict prices for future dates
    predicted_prices = model.predict(future_df)

    # Calculate prediction intervals
    std_dev = np.std([tree.predict(future_df) for tree in model.estimators_], axis=0)
    margin_of_error = 1.96 * std_dev  # 95% confidence interval
    lower_prediction_interval = predicted_prices - margin_of_error
    upper_prediction_interval = predicted_prices + margin_of_error

    # Combine future dates, predicted prices, and prediction intervals
    forecast_df = pd.DataFrame({
        'Date': future_dates,
        'Predicted_Price': predicted_prices,
        'Lower_Prediction_Interval': lower_prediction_interval,
        'Upper_Prediction_Interval': upper_prediction_interval
    })

    # Render prediction result template with forecast_df
    return render_template('prediction_result.html', commodity=commodity, forecast_df=forecast_df.to_html())

# Route to handle the visualization request
@app.route('/visualize', methods=['POST'])
def visualize():
    # Retrieve commodity and forecast data from the form
    commodity = request.form['commodity']
    forecast_df = pd.read_html(request.form['forecast_df'], index_col=0)[0]

    # Plot forecasted prices
    plt.figure(figsize=(8, 6))

    # Plotting predicted prices
    plt.plot(forecast_df['Date'], forecast_df['Predicted_Price'], color='green', label='Predicted Price')

    # Plotting prediction intervals
    plt.fill_between(forecast_df['Date'], forecast_df['Lower_Prediction_Interval'], forecast_df['Upper_Prediction_Interval'], color='blue', alpha=0.2, label='95% Confidence Interval')

    # Add labels and title
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.title(f'Forecasted Prices with Prediction Intervals for {commodity}')
    plt.legend()

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)

    # Save the plot to a BytesIO object
    img = BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0) 

    # Clear the plot
    plt.clf()

    # Return the plot as an image file
    return send_file(img, mimetype='image/png')

#Route to handle Volumes Traded for each commodity
@app.route('/Volumes_traded',methods=['post'])
def volumes():
    forecast_period = int(request.form['forecast_period'])
    start_date = request.form['start_date']
    df['date'] = pd.to_datetime(df['date'])

    # What to predict?
    prediction = 'volume'

    # Dictionary to store total volume traded for each commodity
    total_volume_traded = {}

    # Loop through each commodity
    for commodity in df['commodity'].unique():
        # Filter data for selected commodity
        df_commodity = df[df['commodity'] == commodity]

        # Sort values by date
        df_commodity.sort_values(by='date', inplace=True)

        # Reset index
        df_commodity.reset_index(drop=True, inplace=True)

        # Generate future dates for forecasting
        last_date = df_commodity['date'].max()
        future_dates = pd.date_range(start=last_date, periods=forecast_period, freq='D')

        # Feature engineering: Extracting day, month, and year from Date
        df_commodity['Day'] = df_commodity['date'].dt.day
        df_commodity['Month'] = df_commodity['date'].dt.month
        df_commodity['Year'] = df_commodity['date'].dt.year

        # Splitting data into features (X) and target (y)
        X = df_commodity[['Day', 'Month', 'Year']]
        y = df_commodity[prediction]

        # Train the Random Forest Regressor model
        model2 = train_model(df_commodity, prediction)

        # Feature engineering for future dates
        future_df = pd.DataFrame({
            'Day': future_dates.day,
            'Month': future_dates.month,
            'Year': future_dates.year
        })

        # Predict volume traded for future dates
        predicted_volume_traded = model2.predict(future_df[['Day', 'Month', 'Year']])

        # Sum predicted volume traded for the commodity
        total_volume_traded[commodity] = np.sum(predicted_volume_traded)

    # Plot the total volume traded for each commodity
    plt.figure(figsize=(10, 6))
    plt.bar(total_volume_traded.keys(), total_volume_traded.values())
    plt.xlabel('Commodity')
    plt.ylabel('Total Volume Traded')
    plt.title('Total Volume Traded for Each Commodity')
    plt.xticks(rotation=45, ha='right')

    # Save the plot to a BytesIO object
    #img = BytesIO()
    #plt.savefig(img, format='png')
    #img.seek(0)
    #plot_url = base64.b64encode(img.getvalue()).decode()
    #plt.close()

    #return render_template('prediction_result.html',total_volume_traded=total_volume_traded, plot_url=plot_url)

    img = BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0) 

    # Clear the plot
    plt.clf()

    # Return the plot as an image file
    return send_file(img, mimetype='image/png')


if __name__ == '__main__':
    app.run(debug=True)
