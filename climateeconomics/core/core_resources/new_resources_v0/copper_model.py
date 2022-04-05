

from ntpath import join
from posixpath import dirname
import numpy as np
import pandas as pd


class CopperModel :

    YEAR_START = 2020
    YEAR_END = 2100
    DEMAND = 'All_Demand'
    COPPER_STOCK = 'copper_stock'
    COPPER_PRICE = 'copper_price'
    COPPER_RESERVE = 'copper_reserve'
    PRODUCTION = 'production'
    INITIAL_RESERVE = 'initial_copper_reserve'
    INITIAL_STOCK = 'initial_copper_stock'


    def __init__(self, copper_demand, annual_extraction):
        self.copper_demand = pd.DataFrame() #DataFrame avec la demande par année en cuivre
        self.annual_extraction = annual_extraction

        data_dir = join(dirname(dirname(__file__)), 'sos_wrapping', 'data')

        self.copper_stock =  pd.DataFrame(columns = ['Year', 'Stock']) #pd.read_csv(join(data_dir, 'copper_previous_stock.csv'))  
        self.copper_reserve = pd.DataFrame(columns = ['Year', 'Reserve']) #DataFrame with the wolrd's reserve updated each year
        self.copper_prod_price = pd.DataFrame(columns = ['Year','Price/t', 'Total Price'])#DataFrame with prod price updated each year
        self.copper_prod = pd.DataFrame(columns = ['Year', 'Extraction', 'World Production', 'Cumulated World Production', 'Ratio'])


    
    

    def compute(self, copper_demand, period_of_exploitation):
        
        self.copper_demand = copper_demand
        years = np.arange(2020, 2101, 1)

        # filling the column Year
        self.copper_demand['Year'] = years
        self.copper_prod_price['Year'] = years
        self.copper_reserve['Year'] = years
        self.copper_prod['Year'] = years
        self.copper_stock['Year'] = years

        # put the years as index
        self.copper_demand.index = self.copper_demand['Year'].values
        self.copper_prod_price.index = self.copper_prod_price['Year'].values
        self.copper_stock.index = self.copper_stock['Year'].values
        self.copper_reserve.index = self.copper_reserve['Year'].values
        self.copper_prod.index = self.copper_prod['Year'].values

        # initializing every column
        self.copper_prod['Extraction'] = self.annual_extraction
        self.copper_prod['World Production'] = np.linspace(0,0,len(years))
        self.copper_prod['Cumulated World Production'] = np.linspace(0,0,len(years))
        self.copper_prod['Ratio'] = np.linspace(0,0,len(years))
        self.copper_reserve['Reserve'] = np.linspace(0,0,len(years))
        self.copper_prod_price['Total Price'] = np.linspace(0,0,len(years))
        self.copper_stock['Stock'] = np.linspace(0,0,len(years))
        self.copper_prod_price['Price/t'] = np.linspace(0,0,len(years))

        

        
        for year in period_of_exploitation :           

            
            # reserves update
            self.compute_copper_reserve(year)
            # stock and production update
            self.compute_copper_stock_and_production(year)
            # determines yearly production price
            self.compute_copper_price(year)


    #### méthodes statiques

  
    def compute_copper_reserve(self, year):
        copper_extraction = self.copper_prod.loc[year, 'Extraction']

        if year == self.YEAR_START :
            remainig_copper = 3500 #self.INITIAL_RESERVE['default']
       
        else :
            remainig_copper = self.copper_reserve.loc[year -1, 'Reserve']
        
                          
        # If we want to extract more than what is available, we only extract the available
        if remainig_copper < copper_extraction :
            self.copper_reserve.loc[year, 'Reserve']= 0
                                    
            self.copper_prod.loc[year, 'Extraction']= remainig_copper
            
          
        # If the reserves fall too low, we diminish the extraction
        elif  remainig_copper < 500 :
            self.copper_prod.loc[year, 'Extraction'] = 0.95 * self.copper_prod.loc[year , 'Extraction']
            self.copper_reserve.loc[year, 'Reserve'] = remainig_copper - self.copper_prod.loc[year, 'Extraction']
                                        
            
        else :
            self.copper_reserve.loc[year, 'Reserve'] = remainig_copper - copper_extraction
        
        if self.copper_demand.loc[year, 'Demand']  != 0 :
            ratio = self.copper_prod.loc[year, 'Extraction'] / self.copper_demand.loc[year, 'Demand'] 
            self.copper_prod.loc[year, 'Ratio'] = min(1, ratio)
    
        

    def compute_copper_stock_and_production(self, year) :

        if year == self.YEAR_START :
            old_stock = 880 #self.INITIAL_STOCK['default']
        else :
            old_stock = self.copper_stock.at[year -1, 'Stock']        
       
        
        extraction = self.copper_prod.at[year, 'Extraction']
        copper_demand = self.copper_demand.at[year, 'Demand'] 

        # Stock of the previous year with the extracted minerals, to which we remove the copper demand
        #If the demand is too much and exceeds the stock, then there is no more stock
        new_stock = old_stock + extraction - copper_demand
    

        if new_stock < 0 :
            self.copper_stock.at[year, 'Stock']= 0
                                    
            #If no more Stock, the production is the extracted copper plus what remained of the previous stock (both can be null)
            self.copper_prod.at[year, 'World Production'] = extraction + old_stock
        else :
            self.copper_stock.at[year, 'Stock'] = new_stock
                                    
            #if there is still stock, it means the demand was satified
            self.copper_prod.at[year, 'World Production'] = copper_demand
        
        if year == self.YEAR_START :
            self.copper_prod.at[year, 'Cumulated World Production'] = self.copper_prod.at[year, 'World Production']
        else : 
            self.copper_prod.at[year, 'Cumulated World Production'] = self.copper_prod.at[year -1, 'Cumulated World Production'] + self.copper_prod.at[year, 'World Production']
             
            


    
    def compute_copper_price (self, year) :

        if year ==  self.YEAR_START :
            self.copper_prod_price.loc[year, 'Price/t'] = 9780 

        else :     
            # when there is too much of a difference between the demand and the effective extraction, the prices rise
            if self.copper_demand.loc[year, 'Demand'] - self.copper_prod.loc[year, 'Extraction'] > 5 :
                self.copper_prod_price.loc[year, 'Price/t'] = self.copper_prod_price.loc[year - 1, 'Price/t'] * 1.01
            else :
                self.copper_prod_price.loc[year, 'Price/t'] = self.copper_prod_price.loc[year - 1, 'Price/t']
        
       
        self.copper_prod_price.loc[year, 'Total Price']= self.copper_prod.loc[year, 'World Production'] *  self.copper_prod_price.loc[year, 'Price/t'] *1000 #conversion Mt
        
    
