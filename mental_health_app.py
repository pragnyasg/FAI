import streamlit as st
import pandas as pd
import io 

st.title("🧠 Student Mental Health Risk Evaluator")
st.markdown("---")

uploaded_file = st.file_uploader("Upload your Excel file (must contain ALL 27 required columns)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        
        # --- Define ALL required columns (27 in total) ---
        required_columns = [
            'Student number', 'Hours_Sleep', 'Social_Support_Score', 'Academic_Pressure', 
            'Symptoms_Frequency', 'CGPA', 'Year_of_Study', 'Interested_in_Course', 
            'Family_Pressure', 'Career_Pressure', 'Experienced_Trauma', 'Someone_to_Talk_To', 
            'Sleep_Quality_Rating', 'Screen_Time_Hours', 'Sought_Professional_Help', 
            'Overwhelmed_by_Studies', 'Anxious_in_Social_Situations', 'Physical_Exercise_Frequency', 
            'Close_Friends_Count', 'Motivated_about_Prospects', 'Daily_Energy_Levels', 
            'Knows_Healthy_Coping', 'Skip_Meals_Irregularly', 'Alcohol_Drinks_Weekly', 
            'Recreational_Drugs_Use', 'Difficulty_Controlling_Anger', 'Academic_Satisfaction'
        ]
        
        # Ensure list contains only unique columns
        required_columns = list(set(required_columns)) 
        
        if not all(col in df.columns for col in required_columns):
            missing = list(set(required_columns) - set(df.columns))
            st.error(f"❌ Error: The uploaded file is missing one or more required columns for the full evaluation. Please check spelling. Missing columns: {missing}")
        else:
            
            # --- START OF: Data Processing and Scoring Logic ---
            
            # --- 1. Data Cleaning/Mapping (Creating Score_XXX columns for binary inputs) ---
            
            mapping_risk = {'yes': 1, 'no': 0} # 1 = Higher Risk
            mapping_reverse_risk = {'yes': 0, 'no': 1} # 1 = Higher Risk (Lack of resource)
            
            # Columns where "Yes" maps to 1 (Risk)
            binary_cols_risk = [
                'Interested_in_Course', 'Family_Pressure', 'Career_Pressure', 'Experienced_Trauma', 
                'Overwhelmed_by_Studies', 'Anxious_in_Social_Situations', 'Motivated_about_Prospects',
                'Knows_Healthy_Coping', 'Skip_Meals_Irregularly', 'Recreational_Drugs_Use',
                'Sought_Professional_Help' # Seeked help is treated neutrally/positively in scoring, but mapped here
            ]
            
            # Columns where "No" maps to 1 (Risk - lack of resource)
            binary_reverse_cols = ['Someone_to_Talk_To'] 
            
            # Apply mappings to create intermediate score columns (Score_...)
            for col in binary_cols_risk:
                # Note: We create Score_XXX columns that are either 1 or 0
                df[f'Score_{col}'] = df[col].astype(str).str.lower().map(mapping_risk).fillna(0)
            
            for col in binary_reverse_cols:
                df[f'Score_{col}'] = df[col].astype(str).str.lower().map(mapping_reverse_risk).fillna(1)
            
            # --- 2. Calculate weighted scores (Applying weights to all factors) ---
            
            # A. CORE HEALTH FACTORS
            df['Score_Sleep_Hours'] = (8 - df['Hours_Sleep']).clip(lower=0, upper=4) * 1.5 
            df['Score_Sleep_Quality'] = (5 - df['Sleep_Quality_Rating']).clip(lower=0, upper=4) * 2.0
            df['Score_Symptoms'] = df['Symptoms_Frequency'] * 3.0
            df['Score_Support_Score'] = (5 - df['Social_Support_Score']).clip(lower=0, upper=4) * 1.5
            df['Score_Friends'] = (5 - df['Close_Friends_Count']).clip(lower=0, upper=5) * 1.0
            df['Score_Energy'] = (5 - df['Daily_Energy_Levels']).clip(lower=0, upper=4) * 1.5
            
            # B. ACADEMIC/ENVIRONMENTAL FACTORS
            df['Score_Pressure_Academic_Scale'] = df['Academic_Pressure'] * 1.5
            # FIXED: Referencing the Score_XXX columns created in step 1
            df['Score_Pressure_Family_Binary'] = df['Score_Family_Pressure'] * 2.0 
            df['Score_Pressure_Career_Binary'] = df['Score_Career_Pressure'] * 1.5
            df['Score_CGPA'] = (4.0 - df['CGPA']).clip(lower=0, upper=4.0) * 1.5
            df['Score_Acad_Dissatisfaction'] = (5 - df['Academic_Satisfaction']).clip(lower=0) * 1.0
            df['Score_Overwhelmed'] = df['Score_Overwhelmed_by_Studies'] * 2.0
            
            # C. LIFESTYLE AND TRAUMA FACTORS
            df['Score_Trauma'] = df['Score_Experienced_Trauma'] * 5.0 
            df['Score_Drugs'] = df['Score_Recreational_Drugs_Use'] * 8.0 
            df['Score_Alcohol'] = df['Alcohol_Drinks_Weekly'].clip(upper=15) * 0.7 
            df['Score_Anger'] = df['Difficulty_Controlling_Anger'] * 1.5 
            df['Score_Screen_Time'] = (df['Screen_Time_Hours'] - 7).clip(lower=0) * 0.5
            df['Score_Exercise'] = (5 - df['Physical_Exercise_Frequency']).clip(lower=0) * 1.0
            df['Score_Diet'] = df['Score_Skip_Meals_Irregularly'] * 1.5
            df['Score_Social_Anxiety'] = df['Score_Anxious_in_Social_Situations'] * 1.5
            df['Score_Coping'] = df['Score_Knows_Healthy_Coping'] * 2.0 # Lack of coping is risk

            # We use the created score columns for support/resources:
            df['Score_Lack_Support'] = df['Score_Someone_to_Talk_To'] * 1.5
            df['Score_Lack_Motivation'] = df['Score_Motivated_about_Prospects'] * 1.5
            
            # D. Neutral Factor (Sought help): Neutral weight (1 or 0 score is fine)
            # df['Score_Sought_Professional_Help'] = df['Score_Sought_Professional_Help'] * 0.0 
            
            # 3. Sum all scores to get the final Risk_Score
            score_cols = [col for col in df.columns if col.startswith('Score_')]
            df['Risk_Score'] = df[score_cols].sum(axis=1)
            
            # 4. Determine Risk_Level based on the score thresholds
            def get_risk_level(score):
                if score >= 50:
                    return 'Critical Risk 🚨'
                elif score >= 30:
                    return 'High Risk 🔴'
                elif score >= 15:
                    return 'Moderate Risk 🟠'
                else:
                    return 'Low Risk 🟢'

            df['Risk_Level'] = df['Risk_Score'].apply(get_risk_level)
            
            # Clean up the report dataframe
            df_report = df.drop(columns=[col for col in df.columns if col.startswith('Score_')], errors='ignore')
            
            # --- END OF: Data Processing and Scoring Logic ---

            st.success("✅ Comprehensive Report generated successfully!")

            st.subheader("📋 Top Risk Results")
            st.dataframe(df_report[['Student number', 'Risk_Score', 'Risk_Level', 'CGPA', 'Experienced_Trauma', 'Recreational_Drugs_Use', 'Screen_Time_Hours']].sort_values(by='Risk_Score', ascending=False), hide_index=True)

            # --- Download Button Setup ---
            
            @st.cache_data
            def convert_df_to_excel(df_to_convert):
                """Converts the DataFrame to an Excel file stored in a BytesIO buffer."""
                output = io.BytesIO() 
                df_to_convert.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                return output.read()

            excel_data = convert_df_to_excel(df_report)

            st.download_button(
                label="📥 Download Full Report (.xlsx)",
                data=excel_data,
                file_name="Comprehensive_Mental_Health_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        # Catch unexpected errors (like data type issues if Excel input is poor)
        st.error(f"An unexpected error occurred during file processing. Please ensure all data types are correct (numbers for scores/hours, Yes/No for binary). Error: {e}")