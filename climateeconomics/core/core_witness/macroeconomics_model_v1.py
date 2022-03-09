'''
Copyright 2022 Airbus SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import numpy as np
import pandas as pd
from copy import deepcopy


class MacroEconomics():
    '''
    Economic model that compute the evolution of capital, consumption, output...
    '''
    PC_CONSUMPTION_CONSTRAINT = 'pc_consumption_constraint'

    def __init__(self, param):
        '''
        Constructor
        '''
        self.param = param
        self.inputs = None
        self.economics_df = None
        self.set_data()
        self.create_dataframe()

    def set_data(self):
        self.year_start = self.param['year_start']
        self.year_end = self.param['year_end']
        self.time_step = self.param['time_step']

        self.productivity_start = self.param['productivity_start']
        self.init_gross_output = self.param['init_gross_output']
        self.capital_start = self.param['capital_start']
        self.population_df = self.param['population_df']
        self.population_df.index = self.population_df['years'].values
        self.productivity_gr_start = self.param['productivity_gr_start']
        self.decline_rate_tfp = self.param['decline_rate_tfp']
        self.depreciation_capital = self.param['depreciation_capital']
        self.init_rate_time_pref = self.param['init_rate_time_pref']
        self.conso_elasticity = self.param['conso_elasticity']
        self.lo_capital = self.param['lo_capital']
        self.lo_conso = self.param['lo_conso']
        self.lo_per_capita_conso = self.param['lo_per_capita_conso']
        self.hi_per_capita_conso = self.param['hi_per_capita_conso']
        self.ref_pc_consumption_constraint = self.param['ref_pc_consumption_constraint']
        self.nb_per = round(
            (self.param['year_end'] -
             self.param['year_start']) /
            self.param['time_step'] +
            1)
        self.years_range = np.arange(
            self.year_start,
            self.year_end + 1,
            self.time_step)
        self.frac_damage_prod = self.param['frac_damage_prod']
        self.damage_to_productivity = self.param['damage_to_productivity']
        self.init_output_growth = self.param['init_output_growth']
        self.output_alpha = self.param['output_alpha']
        self.output_gamma = self.param['output_gamma']
        self.energy_eff_k = self.param['energy_eff_k']
        self.energy_eff_cst = self.param['energy_eff_cst']
        self.energy_eff_xzero = self.param['energy_eff_xzero']
        self.energy_eff_max = self.param['energy_eff_max']
        self.capital_utilisation_ratio = self.param['capital_utilisation_ratio']
        self.co2_emissions_Gt = self.param['co2_emissions_Gt']
        self.co2_taxes = self.param['CO2_taxes']
        self.co2_tax_efficiency = self.param['CO2_tax_efficiency']
        self.scaling_factor_energy_investment = self.param['scaling_factor_energy_investment']

        if self.co2_tax_efficiency is not None:
            if 'years' in self.co2_tax_efficiency:
                self.co2_tax_efficiency.index = self.co2_tax_efficiency['years']
            else:
                raise Exception(
                    'Miss a column years in CO2 tax efficiency to set index of the dataframe')

        self.co2_invest_limit = self.param['co2_invest_limit']
        #Employment rate param 
        self.employment_a_param =  self.param['employment_a_param']
        self.employment_power_param = self.param['employment_power_param']
        self.employment_rate_base_value = self.param['employment_rate_base_value']

    def create_dataframe(self):
        '''
        Create the dataframe and fill it with values at year_start
        '''
        default_index = np.arange(
            self.year_start, self.year_end + 1, self.time_step)
        param = self.param
        economics_df = pd.DataFrame(
            index=default_index,
            columns=['years',
                     'gross_output',
                     'net_output',
                     'productivity',
                     'productivity_gr',
                     'consumption',
                     'pc_consumption',
                     'capital',
                     'investment',
                     'energy_investment',
                     'energy_investment_wo_tax',
                     'energy_investment_from_tax',
                     'output_growth'])

        for key in economics_df.keys():
            economics_df[key] = 0
        economics_df['years'] = self.years_range
        economics_df.loc[param['year_start'],
                         'gross_output'] = self.init_gross_output
        economics_df.loc[param['year_start'], 'capital'] = self.capital_start
        economics_df.loc[param['year_start'],
                         'productivity'] = self.productivity_start
        economics_df.loc[param['year_start'],
                         'productivity_gr'] = self.productivity_gr_start
        economics_df.loc[param['year_start'],
                         'output_growth'] = self.init_output_growth
#         economics_df['saving_rate'] = self.saving_rate
        self.economics_df = economics_df
        self.economics_df = self.economics_df.replace(
            [np.inf, -np.inf], np.nan)

        self.energy_investment_wo_renewable = pd.DataFrame(
            index=default_index,
            columns=['years',
                     'energy_investment_wo_renewable'])
        self.energy_investment_wo_renewable['years'] = self.years_range

        energy_investment = pd.DataFrame(
            index=default_index,
            columns=['years',
                     'energy_investment'])

        for key in energy_investment.keys():
            energy_investment[key] = 0
        energy_investment['years'] = self.years_range
        self.energy_investment = energy_investment
        self.energy_investment = self.energy_investment.replace(
            [np.inf, -np.inf], np.nan)
        #workforce_df       
        workforce_df = pd.DataFrame(index=default_index, columns=['years',
                     'employment_rate', 'workforce'])
        for key in workforce_df.keys():
            workforce_df[key] = 0
        workforce_df['years'] = self.years_range
        self.workforce_df = workforce_df
        #Usable capital df
        usable_capital_df = pd.DataFrame(index=default_index, columns=['years',
                     'ennergy_efficiency', 'e_max', 'usable_capital'])
        for key in usable_capital_df.keys():
            usable_capital_df[key] = 0
        usable_capital_df['years'] = self.years_range
        self.usable_capital_df = usable_capital_df

        return economics_df.fillna(0.0), energy_investment.fillna(0.0), 
    
    def set_coupling_inputs(self):
        """
        Set couplings inputs with right index, scaling... 
        """
        self.damefrac = self.inputs['damage_frac_output']
        self.damefrac.index = self.damefrac['years'].values
        #Scale energy production
        self.scaling_factor_energy_production = self.inputs['scaling_factor_energy_production']
        self.scaling_factor_energy_investment = self.inputs['scaling_factor_energy_investment']
        self.energy_production = self.inputs['energy_production'].copy(deep=True)
        self.energy_production['Total production'] *= self.scaling_factor_energy_production
        self.co2_emissions_Gt = pd.DataFrame({'years': self.inputs['co2_emissions_Gt']['years'].values,
                                              'Total CO2 emissions': self.inputs['co2_emissions_Gt']['Total CO2 emissions'].values})
        self.co2_emissions_Gt.index = self.co2_emissions_Gt['years'].values
        self.co2_taxes = self.inputs['CO2_taxes']
        self.co2_taxes.index = self.co2_taxes['years'].values
        self.energy_production.index = self.energy_production['years'].values
        #Investment in energy 
        self.share_energy_investment = pd.Series(
            self.inputs['share_energy_investment']['share_investment'].values / 100.0, index=self.years_range)
        self.total_share_investment = pd.Series(
            self.inputs['total_investment_share_of_gdp']['share_investment'].values / 100.0, index=self.years_range)
        self.share_n_energy_investment = self.total_share_investment - self.share_energy_investment
        #Population dataframes 
        self.population_df = self.inputs['population_df']
        self.population_df.index = self.population_df['years'].values
        self.working_age_population_df = self.inputs['working_age_population_df']
        self.working_age_population_df.index = self.working_age_population_df['years'].values

    def compute_employment_rate(self):
        """ 
        Compute the employment rate. based on prediction from ILO 
        We model a recovery from 2020 crisis until 2031 where past level is reached 
        For all year not in (2020,2031), value = employment_rate_base_value
        """
        year_covid = 2020
        year_end_recovery = 2031
        workforce_df = self.workforce_df
        #For all years employment_rate = base value 
        workforce_df['employment_rate'] = self.employment_rate_base_value 
        #Compute recovery phase
        years_recovery = np.arange(year_covid, year_end_recovery+1)
        x_recovery = years_recovery +1 - year_covid 
        employment_rate_recovery = self.employment_a_param * x_recovery**self.employment_power_param
        employment_rate_recovery_df = pd.DataFrame({'years': years_recovery, 'employment_rate': employment_rate_recovery})
        employment_rate_recovery_df.index = years_recovery
        #Then replace values in original dataframe by recoveries values 
        workforce_df.update(employment_rate_recovery_df)
        
        self.workforce_df = workforce_df
        return workforce_df       
        
    def compute_workforce(self):
        """ Compute the workforce based on formula: 
        workforce = people in working age * employment_rate 
        inputs : - number of people in working age 
                - employment rate in %
        Output: number of working people in million of people
        """
        working_age_pop = self.working_age_population_df['population_1570']
        employment_rate = self.workforce_df['employment_rate']
        workforce = employment_rate * working_age_pop
        self.workforce_df['workforce'] = workforce
        return workforce
    
    def compute_productivity_growthrate(self, year):
        '''
        A_g, Growth rate of total factor productivity.
        Returns:
            :returns: A_g(0) * exp(-Δ_a * (t-1))
        '''
        t = ((year - self.year_start) / self.time_step) + 1
        productivity_gr = self.productivity_gr_start * \
            np.exp(-self.decline_rate_tfp * self.time_step * (t - 1))
        self.economics_df.loc[year, 'productivity_gr'] = productivity_gr
        return productivity_gr

    def compute_productivity(self, year):
        '''
        productivity
        if damage_to_productivity= True add damage to the the productivity
        if  not: productivity evolves independently from other variables (except productivity growthrate)
        '''
        damage_to_productivity = self.damage_to_productivity
        p_productivity = self.economics_df.at[year -
                                              self.time_step, 'productivity']
        p_productivity_gr = self.economics_df.at[year -
                                                 self.time_step, 'productivity_gr']
        damefrac = self.damefrac.at[year, 'damage_frac_output']
        if damage_to_productivity == True:
            #damage = 1-damefrac
            productivity = ((1 - self.frac_damage_prod * damefrac) *
                            (p_productivity / (1 - (p_productivity_gr / (5 / self.time_step)))))
        else:
            productivity = (p_productivity /
                            (1 - (p_productivity_gr / (5 / self.time_step))))
        # we divide the productivity growth rate by 5/time_step because of change in time_step (as
        # advised in Traeger, 2013)
        self.economics_df.loc[year, 'productivity'] = productivity
        return productivity

    def compute_capital(self, year):
        """
        K(t+1), Capital for next time period, trillions $USD
        Args:
            :param capital: capital
            :param depreciation: depreciation rate
            :param investment: investment
        """
        if year == self.year_end:
            pass
        else:
            investment = self.economics_df.at[year, 'investment']
            capital = self.economics_df.at[year, 'capital']
            capital_a = capital * \
                (1 - self.depreciation_capital) ** self.time_step + \
                self.time_step * investment
            # Lower bound for capital
            self.economics_df.loc[year + self.time_step,
                                  'capital'] = max(capital_a, self.lo_capital)
            return capital_a
    
    def compute_emax(self, year):
        """E_max is the maximum energy capital can use to produce output
        E_max = K/(capital_utilisation_ratio*energy_efficiency(year)
        energy_efficiency = 1+ max/(1+exp(-k(x-x0)))
        energy_efficiency is a logistic function because it represent technological progress
        """
        k = self.energy_eff_k
        cst = self.energy_eff_cst
        xo = self.energy_eff_xzero
        capital_utilisation_ratio = self.capital_utilisation_ratio
        max_e = self.energy_eff_max
        #Convert capital in billion
        capital = self.economics_df.loc[year, 'capital']*1e3
        #compute energy_efficiency
        energy_efficiency = cst + max_e/(1+np.exp(-k*(year-xo)))
        #Then compute e_max
        e_max = capital/ (capital_utilisation_ratio * energy_efficiency) 
        
        self.usable_capital_df.loc[year, 'energy_efficiency'] = energy_efficiency
        self.usable_capital_df.loc[year, 'e_max'] = e_max
    
    def compute_usable_capital(self, year):
        """  Usable capital is the part of the capital stock that can be used in the production process. 
        To be usable the capital needs enough energy.
        K_u = K*(E/E_max) 
        E is energy in Twh and K is capital in trill dollars constant 2020
        Output: usable capital in trill dollars constant 2020
        """
        capital = self.economics_df.loc[year, 'capital']
        energy = self.energy_production.at[year,'Total production']
        e_max = self.usable_capital_df.loc[year,'e_max']
        #compute usable capital
        usable_capital = capital * (energy / e_max)  
        self.usable_capital_df.loc[year, 'usable_capital'] = usable_capital

        return usable_capital

    def compute_investment(self, year):
        """
        I(t), Investment, trillions $USD

        """
#         saving_rate = self.saving_rate[year]
        net_output = self.economics_df.at[year, 'net_output']
#         investment = saving_rate * net_output
        energy_investment = self.economics_df.at[year,
                                                 'energy_investment']
        non_energy_investment = self.share_n_energy_investment[year] * net_output
        investment = energy_investment + non_energy_investment
        self.economics_df.loc[year, 'investment'] = investment
        return investment

    def compute_energy_investment(self, year):
        """
        energy_investment(t), trillions $USD (including renewable investments)
        Share of the total output 

        """
        net_output = self.economics_df.at[year, 'net_output']
        energy_investment_wo_tax = self.share_energy_investment[year] * net_output
        
        self.co2_emissions_Gt['Total CO2 emissions'].clip(lower=0.0, inplace=True)

        # store invests without renewable energy
        em_wo_ren = self.energy_investment_wo_renewable
        em_wo_ren.loc[year,'energy_investment_wo_renewable'] = energy_investment_wo_tax * 1e3

        ren_investments = self.compute_energy_renewable_investment(year, energy_investment_wo_tax)
        energy_investment = energy_investment_wo_tax + ren_investments
        self.economics_df.loc[year,
                              ['energy_investment', 'energy_investment_wo_tax', 'energy_investment_from_tax']] = [energy_investment, energy_investment_wo_tax, ren_investments]
        self.energy_investment.loc[year,
                                   'energy_investment'] = energy_investment * 1e3 / self.scaling_factor_energy_investment  # Invest from T$ to G$ coupling variable

        return energy_investment

    def compute_energy_renewable_investment(self, year, energy_investment_wo_tax):
        """
        computes energy investment for renewable part
        for a given year: returns net CO2 emissions * CO2 taxes * a efficiency factor
        """
        co2_invest_limit = self.co2_invest_limit
        emissions = self.co2_emissions_Gt.at[year,'Total CO2 emissions'] * 1e9  # t CO2
        co2_taxes = self.co2_taxes.loc[year, 'CO2_tax']  # $/t
        co2_tax_eff = self.co2_tax_efficiency.at[year,'CO2_tax_efficiency'] / 100.  # %
        ren_investments = emissions * co2_taxes * co2_tax_eff / 1e12  # T$
        i =0
        # if emissions is zero the right gradient (positive) is not zero but the left gradient is zero
        # when complex step we add ren_invest with the complex step and it is
        # not good
        if ren_investments.real == 0.0:
            #print("case 0")
            i+=1
            ren_investments = 0.0
        # Saturation of renewable invest at n * invest wo tax with n ->
        # co2_invest_limit entry parameter
        if ren_investments > co2_invest_limit * energy_investment_wo_tax and ren_investments != 0.0:
            #print(" case max")
            i+=1
            ren_investments = co2_invest_limit * energy_investment_wo_tax / 10.0 * \
                (9.0 + np.exp(- co2_invest_limit *
                              energy_investment_wo_tax / ren_investments))
        #if i ==0: 
            #print('base case')
        return ren_investments
    
    def compute_gross_output(self, year):
        """ Compute the gdp 
        inputs: usable capital by year in trill $ , working population by year in million of people,
             productivity by year (no unit), alpha (between 0 and 1) 
        output: gdp in trillion dollars
        """
        alpha = self.output_alpha
        gamma = self.output_gamma
        productivity = self.economics_df.loc[year,'productivity']
        working_pop = self.workforce_df.loc[year, 'workforce']
        capital_u = self.usable_capital_df.loc[year, 'usable_capital']
        #If gamma == 1/2 use sqrt but same formula 
        if gamma == 1/2:
            output = productivity * (alpha * np.sqrt(capital_u) + (1-alpha)* np.sqrt(working_pop))**2 
        else:
            output = productivity * (alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma)**(1/gamma) 
        self.economics_df.loc[year, 'gross_output'] = output

        return output

    def compute_output_growth(self, year):
        """
        Compute the output growth between year t and year t-1 
        Output growth of the WITNESS model (computed from gross_output_ter)
        """
        if year == self.year_start:
            pass
        else:
            gross_output_ter = self.economics_df.at[year,
                                                    'gross_output']
            gross_output_ter_a = self.economics_df.at[year -
                                                      self.time_step, 'gross_output']
            gross_output_ter = max(1e-6, gross_output_ter)
            output_growth = ((gross_output_ter -
                              gross_output_ter_a) / gross_output_ter) / self.time_step
            self.economics_df.loc[year, 'output_growth'] = output_growth
            return output_growth

    def compute_output_net_of_damage(self, year):
        """
        Output net of damages, trillions USD
        """
        damage_to_productivity = self.damage_to_productivity
        damefrac = self.damefrac.at[year, 'damage_frac_output']
        gross_output = self.economics_df.at[year,
                                                'gross_output']
#        if damage_to_productivity == True :
#            D = 1 - damefrac
#            damage_to_output = D/(1-self.frac_damage_prod*(1-D))
#            output_net_of_d = gross_output * damage_to_output
#            damtoprod = D/(1-self.frac_damage_prod*(1-D))
        if damage_to_productivity == True:
            damage = 1 - ((1 - damefrac) /
                          (1 - self.frac_damage_prod * damefrac))
            output_net_of_d = (1 - damage) * gross_output
        else:
            output_net_of_d = gross_output * (1 - damefrac)
        self.economics_df.loc[year, 'net_output'] = output_net_of_d
        return output_net_of_d

    def compute_consumption(self, year):
        """Equation for consumption
        C, Consumption, trillions $USD
        Args:
            output: Economic output at t
            savings: Savings rate at t
        """
        net_output = self.economics_df.at[year, 'net_output']
        investment = self.economics_df.at[year, 'investment']
        consumption = net_output - investment
        # lower bound for conso
        self.economics_df.loc[year, 'consumption'] = max(
            consumption, self.lo_conso)
        return consumption

    def compute_consumption_pc(self, year):
        """Equation for consumption per capita
        c, Per capita consumption, thousands $USD
        """
        consumption = self.economics_df.at[year, 'consumption']
        population = self.population_df.at[year, 'population']
        consumption_pc = consumption / population * 1000
        # Lower bound for pc conso
        self.economics_df.loc[year, 'pc_consumption'] = max(
            consumption_pc, self.lo_per_capita_conso)
        return consumption_pc

    def compute_comsumption_pc_constraint(self):
        """Equation for consumption per capita constraint
        c, Per capita consumption constraint
        """
        pc_consumption = self.economics_df['pc_consumption'].values
        self.pc_consumption_constraint = (self.hi_per_capita_conso - pc_consumption) \
            / self.ref_pc_consumption_constraint
            
    def compute_global_investment_constraint(self):
        """ Global investment constraint
        """
        self.global_investment_constraint = deepcopy(
            self.inputs['share_energy_investment'])

        self.global_investment_constraint['share_investment'] = self.global_investment_constraint['share_investment'].values / 100.0 + \
            self.share_n_energy_investment.values - \
            self.inputs['total_investment_share_of_gdp']['share_investment'].values / 100.0

    def compute(self, inputs, damage_prod=False):
        """
        Compute all models for year range
        """
        self.create_dataframe()
        self.damage_prod = damage_prod
        self.inputs = inputs
        self.set_coupling_inputs()
        
        #Employment rate and workforce
        self.compute_employment_rate()
        self.compute_workforce()
        # YEAR START
        year_start = self.year_start
        self.compute_emax(year_start)
        self.compute_usable_capital(year_start)
        self.compute_output_net_of_damage(year_start)
        self.compute_energy_investment(year_start)
        self.compute_investment(year_start)
        self.compute_consumption(year_start)
        self.compute_consumption_pc(year_start)   
        # for year 0 compute capital +1
        self.compute_capital(year_start)
        # Then iterate over years from year_start + tstep:
        for year in self.years_range[1:]:
            # First independant variables
            self.compute_productivity_growthrate(year)
            self.compute_productivity(year)
            # Then others:
            self.compute_emax(year)
            self.compute_usable_capital(year)
            self.compute_gross_output(year)
            self.compute_output_net_of_damage(year)
            self.compute_energy_investment(year)
            self.compute_investment(year)
            self.compute_consumption(year)
            self.compute_consumption_pc(year)
            # capital t+1 :
            self.compute_capital(year)
        for year in self.years_range:
            self.compute_output_growth(year)
        self.economics_df = self.economics_df.replace(
            [np.inf, -np.inf], np.nan)
        # Compute consumption per capita constraint 
        self.compute_comsumption_pc_constraint()
        # Compute global investment constraint
        self.compute_global_investment_constraint()

        return self.economics_df.fillna(0.0), self.energy_investment.fillna(0.0), self.global_investment_constraint, \
            self.energy_investment_wo_renewable.fillna(0.0), self.pc_consumption_constraint, self.workforce_df, self.usable_capital_df


    """-------------------Gradient functions-------------------"""
    def compute_dworkforce_dworkagepop(self):
        """ Gradient for workforce wrt working age population 
        """
        years = self.years_range
        nb_years = len(years)

        employment_rate = self.workforce_df['employment_rate'].values
        dworkforce_dworkagepop = np.identity(nb_years)
        dworkforce_dworkagepop *= employment_rate 
        
        return dworkforce_dworkagepop
    
    def compute_dproductivity(self):
        """gradient for productivity for damage_df
        Args:
            output: gradient
        """
        years = np.arange(self.year_start,
                          self.year_end + 1, self.time_step)
        nb_years = len(years)
        p_productivity_gr = self.economics_df['productivity_gr'].values
        p_productivity = self.economics_df['productivity'].values

        # derivative matrix initialization
        d_productivity = np.zeros((nb_years, nb_years))
        if self.damage_to_productivity == True:

            # first line stays at zero since derivatives of initial values are
            # zero
            for i in range(1, nb_years):
                d_productivity[i, i] = (1 - self.frac_damage_prod * self.damefrac.at[years[i], 'damage_frac_output']) * \
                    d_productivity[i - 1, i] / (1 - (p_productivity_gr[i - 1] /
                                                     (5 / self.time_step))) -\
                    self.frac_damage_prod * \
                    p_productivity[i - 1] / \
                    (1 - (p_productivity_gr[i - 1] / (5 / self.time_step)))
                for j in range(1, i):
                    d_productivity[i, j] = (1 - self.frac_damage_prod * self.damefrac.at[years[i], 'damage_frac_output']) * \
                        d_productivity[i - 1, j] / \
                        (1 - (p_productivity_gr[i - 1] / (5 / self.time_step)))

        return d_productivity
    
    def dusablecapital_denergy(self):
        """ Gradient of usable capital wrt energy 
        usable_capital = capital * (energy / e_max)  
        """
        #derivative: capital/e_max 
        years = self.years_range
        nb_years = len(years)
        #Inputs 
        capital = self.economics_df['capital'].values
        e_max = self.usable_capital_df['e_max'].values
        dusablecapital_denergy = np.identity(nb_years) 
        dusablecapital_denergy *= capital/e_max       
        #Is dcapital missing ?
        return dusablecapital_denergy
        
    def dgrossoutput_dworkingpop(self): 
        """ Gradient fo gross output wrt working pop
        gross output = productivity * (alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma)**(1/gamma) 
        """
        years = self.years_range
        nb_years = len(years)
        alpha = self.output_alpha
        gamma = self.output_gamma
        doutput = np.identity(nb_years)
        working_pop = self.workforce_df['workforce'].values
        capital_u = self.usable_capital_df['usable_capital'].values
        productivity = self.economics_df['productivity'].values
        #output = f(g(x)) with f = productivity*g**(1/gamma) a,d g= alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma
        #f'(g) = productivity*(1/gamma)*g**(1/gamma -1)
        #g'(workingpop) = (1-alpha)*gamma*workingpop**(gamma-1)
        #f'(g(x)) = f'(g)*g'(x)
        # first line stays at zero since derivatives of initial values are zero
        g = alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma
        g_prime = (1-alpha)*gamma*working_pop**(gamma-1)
        f_prime = productivity * (1/gamma) * g * g_prime 
        doutput *= f_prime
        doutput[0,0] = 0 
        return doutput 
    
    def dnet_output(self, dgross_output):
        """compute dnet_output using dgross output
        """
        damefrac = self.damefrac['damage_frac_output'].values
        if self.damage_to_productivity == True:
                    dnet_output = (
                        1 - damefrac) / (1 - self.frac_damage_prod * damefrac) * dgross_output
        else:
            dnet_output = (1 - damefrac) * dgross_output
        return dnet_output
    
    def dinvestment(self, dnet_output):
        years = self.years_range
        nb_years = len(years)
        dinvestment =  np.zeros((nb_years, nb_years))
        denergy_investment = np.identity(nb_years)
        denergy_investment *= self.share_energy_investment.values * dnet_output
        # Saturation of renewable invest at n * invest wo tax with n ->
        # co2_invest_limit entry parameter
        for i in range(0, nb_years):
            emissions = self.co2_emissions_Gt.at[years[i],'Total CO2 emissions']
            co2_taxes = self.co2_taxes.at[years[i], 'CO2_tax']
            co2_tax_eff = self.co2_tax_efficiency.at[years[i], 'CO2_tax_efficiency']
            energy_investment_wo_tax = self.economics_df.at[years[i],'energy_investment_wo_tax']
            net_output = self.economics_df.at[years[i], 'net_output']
            ren_investments = emissions * 1e9 * co2_taxes * co2_tax_eff / 100 / 1e12  # T$
            for j in range(0, i + 1):
                if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:

                        denergy_investment[i, j] += self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * 9 / 10 \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] / 10 * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (-1) * self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] / ren_investments \
                            * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments)
                        
                dinvestment[i, j] = denergy_investment[i, j] + self.share_n_energy_investment[years[i]] * dnet_output[i, j]
        return denergy_investment, dinvestment  
   
    def compute_dconsumption(self, dnet_output, dinvestment):
        """gradient computation for consumption
        Args:
            input: gradients of net_output, investment
            output: gradients of consumption
        """
        years = self.years_range
        nb_years = len(years)
        # derivative matrix initialization
        dconsumption = np.zeros((nb_years, nb_years))
        # first line stays at zero since derivatives of initial values are zero
        for i in range(0, nb_years):
            consumption = self.economics_df.at[years[i], 'consumption']
            if consumption == self.lo_conso:
                pass
            else:
                dconsumption[i, i] = dnet_output[i, i] - dinvestment[i, i]
        return dconsumption

    def compute_dconsumption_pc(self, dconsumption):
        """gradient computation for pc_consumption
        Args:
            input: gradients of consumption
            output: gradients of pc_consumption
        """
        years = np.arange(self.year_start,
                          self.year_end + 1, self.time_step)
        nb_years = len(years)
        # derivative matrix initialization
        dconsumption_pc = np.zeros((nb_years, nb_years))
        # first line stays at zero since derivatives of initial values are zero
        for i in range(0, nb_years):
            consumption_pc = self.economics_df.at[years[i], 'pc_consumption']
            if consumption_pc > self.lo_per_capita_conso:
                for j in range(0, i + 1):
                    dconsumption_pc[i, j] = dconsumption[i, j] / \
                        self.population_df.at[years[i], 'population'] * 1000

        return dconsumption_pc
    
    def compute_dconsumption_pc_dpopulation(self):
        """gradient computation for pc_consumption wrt population
        Args:
            output: gradients of pc_consumption
        consumption_pc = consumption / population * 1000
        # Lower bound for pc conso
        self.economics_df.loc[year, 'pc_consumption'] = max(
            consumption_pc, self.lo_per_capita_conso)
        """
        years = self.years_range
        nb_years = len(years)
        dconsumption_pc = np.zeros((nb_years, nb_years))
        for i in range(0, nb_years):
            consumption_pc = self.economics_df.at[years[i], 'pc_consumption']
            consumption = self.economics_df.at[years[i], 'consumption']
            pop = self.population_df.at[years[i], 'population']
            if consumption_pc > self.lo_per_capita_conso:
                dconsumption_pc[i,i] = - consumption*1000/ pop**2 
        return dconsumption_pc
    
    def dgross_output_ddamage(self, dproductivity):
        years = self.years_range
        nb_years = len(years)
        alpha = self.output_alpha
        gamma = self.output_gamma
        doutput = np.identity(nb_years)
        doutput_dprod = np.identity(nb_years)
        working_pop = self.workforce_df['workforce'].values
        capital_u = self.usable_capital_df['usable_capital'].values
        #Derivative of output wrt productivity
        doutput_dprod *= (alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma)**(1/gamma)
        #at zero gross output is an input
        doutput_dprod[0,0] = 0 
        #Then doutput = doutput_d_prod * dproductivity
        doutput *= dproductivity* doutput_dprod
        return doutput
    
    def dnet_output_ddamage(self, dgross_output):
        years = self.years_range
        nb_years = len(years)
        dnet_output = np.zeros((nb_years, nb_years))
        for i in range(0, nb_years):
            output = self.economics_df.at[years[i], 'gross_output']
            damefrac = self.damefrac.at[years[i], 'damage_frac_output']
            for j in range(0, i + 1):
                if i ==j: 
                    if self.damage_to_productivity == True:
                        dnet_output[i, j] = (self.frac_damage_prod - 1) / ((self.frac_damage_prod * damefrac - 1)**2) * output + \
                            (1 - damefrac) / (1 - self.frac_damage_prod *
                                              damefrac) * dgross_output[i, j]
                    else:
                        dnet_output[i, j] = - output + (1 - damefrac) * dgross_output[i, j]
                else:
                    if self.damage_to_productivity == True:
                        dnet_output[i, j] = (1 - damefrac) / (1 - self.frac_damage_prod * damefrac) * dgross_output[i, j]
                    else:
                        dnet_output[i, j] = (1 - damefrac) * dgross_output[i, j]
        return dnet_output 
        
    def dgrossoutput_denergy(self, dcapitalu_denergy):
        years = self.years_range
        nb_years = len(years)
        alpha = self.output_alpha
        gamma = self.output_gamma
        doutput_dcap = np.identity(nb_years)
        working_pop = self.workforce_df['workforce'].values
        capital_u = self.usable_capital_df['usable_capital'].values
        productivity = self.economics_df['productivity'].values
        #Derivative of output wrt capital
        #output = f(g(x)) with f = productivity*g**(1/gamma) a,d g= alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma
        #f'(g) = productivity*(1/gamma)*g**(1/gamma -1)
        #g'(capital) = alpha*gamma*capital**(gamma-1)
        #f'(g(x)) = f'(g)*g'(x)
        g = alpha * capital_u**gamma + (1-alpha)* (working_pop)**gamma
        g_prime = alpha*gamma*capital_u**(gamma-1)
        f_prime = productivity * (1/gamma) * g * g_prime 
        doutput_dcap *= f_prime
        #at zero gross output is an input
        doutput_dcap[0,0] = 0 
        #Then doutput = doutput_d_prod * dproductivity
        doutput = dcapitalu_denergy * doutput_dcap
        return doutput    
    
    def compute_dinvest_dco2taxes(self):
        years = self.years_range
        nb_years = len(years)
        co2_invest_limit = self.co2_invest_limit
        emissions = self.co2_emissions_Gt['Total CO2 emissions'].values * 1e9  # t CO2
        co2_taxes = self.co2_taxes['CO2_tax'].values  # $/t
        co2_tax_eff = self.co2_tax_efficiency['CO2_tax_efficiency'].values / 100.  # %
        energy_investment_wo_tax = self.economics_df['energy_investment_wo_tax'].values
        dren_investments = np.identity(nb_years)

        ren_investments = emissions * co2_taxes * co2_tax_eff / 1e12  # T$
        dren_investments *= emissions * co2_tax_eff/ 1e12
        
        for i in range(0, nb_years):
            if ren_investments[i] >  co2_invest_limit * energy_investment_wo_tax[i] and ren_investments[i] != 0.0:
                g_prime = emissions[i] * co2_tax_eff[i]/ 1e12 
                f_prime =  g_prime * co2_invest_limit * energy_investment_wo_tax[i] / 10.0 * (co2_invest_limit * energy_investment_wo_tax[i]/ren_investments[i]**2)*\
                                                                                 np.exp(- co2_invest_limit * energy_investment_wo_tax[i] / ren_investments[i])
                dren_investments[i,i] = f_prime
            if ren_investments[i].real == 0.0:
                dren_investments[i,i] = 0.0
        # #energy_investment = investwithout + ren_invest then denergy_investment = dren_investments
        denergy_invest = dren_investments
        #investment = energy_investment + non_energy_investment
        dinvestment = denergy_invest 
        return dren_investments, denergy_invest, dinvestment    
                       
    def compute_dtotal_investment_share_of_gdp(self):
        """gradient computation for gross_output, capital, investment, energy_investment, net output for total_investment_share_of_gdp
        Args:
            output: gradients of gross_output, capital, investment, energy_investment, net output
        """
        years = np.arange(self.year_start,
                          self.year_end + 1, self.time_step)
        nb_years = len(years)

        beta = self.output_k_exponent
        alpha = self.output_pop_exponent
        gamma = self.output_energy_exponent
        theta = self.output_exponent
        b = self.output_energy_share
        c = self.output_pop_share
        pop_factor = self.pop_factor
        energy_factor = self.energy_factor

        # derivative matrix initialization
        dgross_output = np.zeros((nb_years, nb_years))
        dcapital = np.zeros((nb_years, nb_years))
        dinvestment = np.zeros((nb_years, nb_years))
        denergy_investment = np.zeros((nb_years, nb_years))
        dnet_output = np.zeros((nb_years, nb_years))

        # first line stays at zero since derivatives of initial values are zero
        for i in range(0, nb_years):

            population = self.population_df.at[years[i], 'population']
            capital = self.economics_df.at[years[i], 'capital']
            energy = self.energy_production.at[years[i],
                                               'Total production']
            productivity = self.economics_df.at[years[i], 'productivity']
            energy_productivity = self.economics_df.at[years[i],
                                                       'energy_productivity']
            net_output = self.economics_df.at[years[i], 'net_output']
            damefrac = self.damefrac.at[years[i], 'damage_frac_output']

            emissions = self.co2_emissions_Gt.at[years[i],
                                                 'Total CO2 emissions']
            co2_taxes = self.co2_taxes.at[years[i], 'CO2_tax']
            co2_tax_eff = self.co2_tax_efficiency.at[years[i],
                                                     'CO2_tax_efficiency']
            energy_investment_wo_tax = self.economics_df.at[years[i],
                                                            'energy_investment_wo_tax']

            ren_investments = emissions * 1e9 * co2_taxes * co2_tax_eff / 100 / 1e12  # T$

            for j in range(0, i + 1):
                if i != 0:
                    energy = max(0, energy)
                    economic_part = max(0, productivity *
                                        (c * (pop_factor * population)**alpha + (1 - c) * (capital)**beta))
                    energy_part = max(0, energy_productivity *
                                      (energy_factor * energy)**gamma)
                    if economic_part == 0:
                        deconomic_part = 0
                    else:
                        deconomic_part = beta * \
                            dcapital[i, j] * productivity * \
                            ((1 - c) * (capital)**(beta - 1))

                    dgross_output[i, j] = theta * b * deconomic_part * \
                        (b * economic_part + (1 - b) * energy_part)**(theta - 1)

                    if self.damage_to_productivity == True:
                        dnet_output[i, j] = (
                            1 - damefrac) / (1 - self.frac_damage_prod * damefrac) * dgross_output[i, j]
                    else:
                        dnet_output[i, j] = (
                            1 - damefrac) * dgross_output[i, j]

                denergy_investment[i, j] = self.share_energy_investment[years[i]
                                                                        ] * dnet_output[i, j]

                # Saturation of renewable invest at n * invest wo tax with n ->
                # co2_invest_limit entry parameter
                if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:

                    denergy_investment[i, j] += self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * 9 / 10 \
                        + self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] / 10 * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments) \
                        + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (-1) * self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] / ren_investments \
                        * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments)

                if i == j:
                    dinvestment[i, j] = denergy_investment[i, j] + \
                        self.share_n_energy_investment[years[i]
                                                       ] * dnet_output[i, j] + net_output
                else:
                    dinvestment[i, j] = denergy_investment[i, j] + \
                        self.share_n_energy_investment[years[i]
                                                       ] * dnet_output[i, j]

                if i < nb_years - 1:
                    capital_after = self.economics_df.at[years[i + 1], 'capital']
                    if capital_after == self.lo_capital:
                        dcapital[i + 1, j] = 0
                    else:
                        dcapital[i + 1, j] = dcapital[i, j] * (
                            1 - self.depreciation_capital) ** self.time_step + self.time_step * dinvestment[i, j]

        return dgross_output, dinvestment, denergy_investment, dnet_output        
                
    def compute_dgross_output_dCO2_taxes(self):
        """gradient computation for gross_output, capital, investment, energy_investment, net output for energy_production
        Args:
            input: none
            output: gradients of gross_output, capital, investment, energy_investment, net output
        """
        years = np.arange(self.year_start,
                          self.year_end + 1, self.time_step)
        nb_years = len(years)

        beta = self.output_k_exponent
        alpha = self.output_pop_exponent
        gamma = self.output_energy_exponent
        theta = self.output_exponent
        b = self.output_energy_share
        c = self.output_pop_share
        pop_factor = self.pop_factor
        energy_factor = self.energy_factor

        # derivative matrix initialization
        dgross_output = np.zeros((nb_years, nb_years))
        dcapital = np.zeros((nb_years, nb_years))
        dinvestment = np.zeros((nb_years, nb_years))
        denergy_investment = np.zeros((nb_years, nb_years))
        dnet_output = np.zeros((nb_years, nb_years))

        economic_part = np.maximum(0, self.economics_df['productivity'].values *
                                   (c * (pop_factor * self.population_df['population'].values) **
                                    alpha + (1 - c) * (self.economics_df['capital'].values)**beta))
        energy_part = np.maximum(0, self.economics_df['energy_productivity'].values *
                                 (energy_factor * np.maximum(0, self.energy_production['Total production'].values))**gamma)

        # first line stays at zero since derivatives of initial values are zero
        for i in range(0, nb_years):

            capital_i = self.economics_df.at[years[i], 'capital']
            productivity_i = self.economics_df.at[years[i],
                                                  'productivity']
            damefrac_i = self.damefrac.at[years[i], 'damage_frac_output']

            emissions = self.co2_emissions_Gt.at[years[i],
                                                 'Total CO2 emissions']
            co2_taxes = self.co2_taxes.at[years[i], 'CO2_tax']
            co2_tax_eff = self.co2_tax_efficiency.at[years[i],
                                                     'CO2_tax_efficiency']
            energy_investment_wo_tax = self.economics_df.at[years[i],
                                                            'energy_investment_wo_tax']
            net_output = self.economics_df.at[years[i], 'net_output']

            ren_investments = emissions * 1e9 * co2_taxes * co2_tax_eff / 100 / 1e12  # T$

            # %
            co2_tax_eff = self.co2_tax_efficiency.at[years[i],
                                                     'CO2_tax_efficiency']

            for j in range(0, i + 1):
                if economic_part[i] == 0:
                    deconomic_part = 0
                else:
                    deconomic_part = dcapital[i, j] * beta * productivity_i * \
                        (1 - c) * (capital_i)**(beta - 1)

                dgross_output[i, j] = theta * (b * deconomic_part) * (
                    b * economic_part[i] + (1 - b) * energy_part[i])**(theta - 1)

                if self.damage_to_productivity == True:
                    dnet_output[i, j] = (
                        1 - damefrac_i) / (1 - self.frac_damage_prod * damefrac_i) * dgross_output[i, j]
                else:
                    dnet_output[i, j] = (1 - damefrac_i) * dgross_output[i, j]

                if i == j:
                    denergy_investment[i, j] = self.share_energy_investment[years[i]
                                                                            ] * dnet_output[i, j] + emissions * co2_tax_eff * 1e9 / 1e12  # T$

                    # Saturation of renewable invest at n * invest wo tax with
                    # n -> co2_invest_limit entry parameter
                    if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:
                        # Base function:
                        # ren_investments = self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0 * \
                        #    (9.0 + np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments))
                        # Derivative:
                        #dren_investments = d(self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output * 9 / 10.0)
                        #  + d(self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0
                        #  * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments))
                        # So d(u*v) = u'.v + u.v' with:
                        #  u = self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0
                        #  v = np.exp(- self.co2_invest_limit * self.share_energy_investment[year] * net_output / ren_investments)
                        # With v'= d(- self.co2_invest_limit * self.share_energy_investment[year] * net_output / ren_investments) * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments)
                        # So d(w/x) = w'.x - w.x' / (x*x) with:
                        #  w = - self.co2_invest_limit * self.share_energy_investment[year] * net_output
                        #  x = ren_investments = emissions * co2_taxes * co2_tax_eff / 1e12 * 1e9
                        denergy_investment[i, j] = self.share_energy_investment[years[i]] * dnet_output[i, j] \
                            + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] * 9 / 10 \
                            + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] / 10 * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (- self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * ren_investments
                                                                                                                  + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output * emissions * co2_tax_eff * 1e9 / 1e12) / (ren_investments * ren_investments) * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments)

                else:
                    denergy_investment[i, j] = self.share_energy_investment[years[i]
                                                                            ] * dnet_output[i, j]

                    if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:
                        denergy_investment[i, j] += self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] * 9 / 10 \
                            + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] / 10 * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (-1) * self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * ren_investments \
                            / (ren_investments * ren_investments) * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments)

                dinvestment[i, j] = denergy_investment[i, j] + \
                    self.share_n_energy_investment[years[i]
                                                   ] * dnet_output[i, j]

                if i < nb_years - 1:
                    capital_after = self.economics_df.at[years[i + 1], 'capital']
                    if capital_after == self.lo_capital:
                        dcapital[i + 1, j] = 0
                    else:
                        dcapital[i + 1, j] = dcapital[i, j] * (
                            1 - self.depreciation_capital) ** self.time_step + self.time_step * dinvestment[i, j]

        return dgross_output, dinvestment, denergy_investment, dnet_output

    def compute_dgross_output_dCO2_emission_gt(self):
        """gradient computation for gross_output, capital, investment, energy_investment, net output for energy_production
        Args:
            input: none
            output: gradients of gross_output, capital, investment, energy_investment, net output
        """
        years = np.arange(self.year_start,
                          self.year_end + 1, self.time_step)
        nb_years = len(years)

        beta = self.output_k_exponent
        alpha = self.output_pop_exponent
        gamma = self.output_energy_exponent
        theta = self.output_exponent
        b = self.output_energy_share
        c = self.output_pop_share
        pop_factor = self.pop_factor
        energy_factor = self.energy_factor

        # derivative matrix initialization
        dgross_output = np.zeros((nb_years, nb_years))
        dcapital = np.zeros((nb_years, nb_years))
        dinvestment = np.zeros((nb_years, nb_years))
        denergy_investment = np.zeros((nb_years, nb_years))
        dnet_output = np.zeros((nb_years, nb_years))

        economic_part = np.maximum(0, self.economics_df['productivity'].values *
                                   (c * (pop_factor * self.population_df['population'].values) **
                                    alpha + (1 - c) * (self.economics_df['capital'].values)**beta))
        energy_part = np.maximum(0, self.economics_df['energy_productivity'].values *
                                 (energy_factor * np.maximum(0, self.energy_production['Total production'].values))**gamma)

        # first line stays at zero since derivatives of initial values are zero
        for i in range(0, nb_years):

            capital_i = self.economics_df.at[years[i], 'capital']
            productivity_i = self.economics_df.at[years[i],
                                                  'productivity']
            damefrac_i = self.damefrac.at[years[i], 'damage_frac_output']

            emissions = self.co2_emissions_Gt.at[years[i],
                                                 'Total CO2 emissions']
            co2_taxes = self.co2_taxes.at[years[i], 'CO2_tax']
            co2_tax_eff = self.co2_tax_efficiency.at[years[i],
                                                     'CO2_tax_efficiency']
            energy_investment_wo_tax = self.economics_df.at[years[i],
                                                            'energy_investment_wo_tax']
            net_output = self.economics_df.at[years[i], 'net_output']

            ren_investments = emissions * 1e9 * co2_taxes * co2_tax_eff / 100 / 1e12  # T$

            for j in range(0, i + 1):

                if economic_part[i] == 0:
                    deconomic_part = 0
                else:
                    deconomic_part = dcapital[i, j] * beta * productivity_i * \
                        (1 - c) * (capital_i)**(beta - 1)

                dgross_output[i, j] = theta * (b * deconomic_part) * (
                    b * economic_part[i] + (1 - b) * energy_part[i])**(theta - 1)

                if self.damage_to_productivity == True:
                    dnet_output[i, j] = (
                        1 - damefrac_i) / (1 - self.frac_damage_prod * damefrac_i) * dgross_output[i, j]
                else:
                    dnet_output[i, j] = (1 - damefrac_i) * dgross_output[i, j]

                if i == j:
                    denergy_investment[i, j] = self.share_energy_investment[years[i]
                                                                            ] * dnet_output[i, j] + np.sign(emissions) * co2_taxes * co2_tax_eff * 1e9 / 1e12  # T$

                    # Saturation of renewable invest at n * invest wo tax with
                    # n -> co2_invest_limit entry parameter
                    if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:
                        # Base function:
                        # ren_investments = self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0 * \
                        #    (9.0 + np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments))
                        # Derivative:
                        #dren_investments = d(self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output * 9 / 10.0)
                        #  + d(self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0
                        #  * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments))
                        # So d(u*v) = u'.v + u.v' with:
                        #  u = self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0
                        #  v = np.exp(- self.co2_invest_limit * self.share_energy_investment[year] * net_output / ren_investments)
                        # With v'= d(- self.co2_invest_limit * self.share_energy_investment[year] * net_output / ren_investments) * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments)
                        # So d(w/x) = w'.x - w.x' / (x*x) with:
                        #  w = - self.co2_invest_limit * self.share_energy_investment[year] * net_output
                        #  x = ren_investments = emissions * co2_taxes * co2_tax_eff / 1e12 * 1e9
                        denergy_investment[i, j] = self.share_energy_investment[years[i]] * dnet_output[i, j] \
                            + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] * 9 / 10 \
                            + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] / 10 * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (- self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * ren_investments
                                                                                                                  + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output * co2_taxes * co2_tax_eff * 1e9 / 1e12) / (ren_investments * ren_investments) * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments)

                else:
                    denergy_investment[i, j] = self.share_energy_investment[years[i]
                                                                            ] * dnet_output[i, j]

                    if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:
                        denergy_investment[i, j] += self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] * 9 / 10 \
                            + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]] / 10 * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (-1) * self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * ren_investments \
                            / (ren_investments * ren_investments) * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments)

                dinvestment[i, j] = denergy_investment[i, j] + \
                    self.share_n_energy_investment[years[i]
                                                   ] * dnet_output[i, j]

                if i < nb_years - 1:
                    capital_after = self.economics_df.at[years[i + 1], 'capital']
                    if capital_after == self.lo_capital:
                        dcapital[i + 1, j] = 0
                    else:
                        dcapital[i + 1, j] = dcapital[i, j] * (
                            1 - self.depreciation_capital) ** self.time_step + self.time_step * dinvestment[i, j]

        return dgross_output, dinvestment, denergy_investment, dnet_output

    def compute_dshare_energy_investment(self):
        """gradient computation for gross_output, capital, investment, energy_investment, net output for energy_production
        Args:
            input: gradients of energy_productivity, productivity
            output: gradients of gross_output, capital, investment, energy_investment, net output
        """
        years = np.arange(self.year_start,
                          self.year_end + 1, self.time_step)
        nb_years = len(years)

        beta = self.output_k_exponent
        alpha = self.output_pop_exponent
        gamma = self.output_energy_exponent
        theta = self.output_exponent 
        b = self.output_energy_share
        c = self.output_pop_share
        pop_factor = self.pop_factor
        energy_factor = self.energy_factor

        # derivative matrix initialization
        dgross_output = np.zeros((nb_years, nb_years))
        dcapital = np.zeros((nb_years, nb_years))
        dinvestment = np.zeros((nb_years, nb_years))
        denergy_investment = np.zeros((nb_years, nb_years))
        dnet_output = np.zeros((nb_years, nb_years))

        economic_part = np.maximum(0, self.economics_df['productivity'].values *
                                   (c * (pop_factor * self.population_df['population'].values) **
                                    alpha + (1 - c) * (self.economics_df['capital'].values)**beta))
        energy_part = np.maximum(0, self.economics_df['energy_productivity'].values *
                                 (energy_factor * np.maximum(0, self.energy_production['Total production'].values))**gamma)

        # first line stays at zero since derivatives of initial values are zero
        for i in range(0, nb_years):

            capital_i = self.economics_df.at[years[i], 'capital']
            productivity_i = self.economics_df.at[years[i],
                                                  'productivity']
            damefrac_i = self.damefrac.at[years[i], 'damage_frac_output']

            co2_tax_eff = self.co2_tax_efficiency.at[years[i],
                                                     'CO2_tax_efficiency']
            emissions = self.co2_emissions_Gt.at[years[i],
                                                 'Total CO2 emissions']
            co2_taxes = self.co2_taxes.at[years[i], 'CO2_tax']
            co2_tax_eff = self.co2_tax_efficiency.at[years[i],
                                                     'CO2_tax_efficiency']
            energy_investment_wo_tax = self.economics_df.at[years[i],
                                                            'energy_investment_wo_tax']
            net_output = self.economics_df.at[years[i], 'net_output']

            ren_investments = emissions * 1e9 * co2_taxes * co2_tax_eff / 100 / 1e12  # T$

            for j in range(0, i + 1):

                if economic_part[i] == 0:
                    deconomic_part = 0
                else:
                    deconomic_part = dcapital[i, j] * beta * productivity_i * \
                        (1 - c) * (capital_i)**(beta - 1)

                dgross_output[i, j] = theta * (b * deconomic_part) * (
                    b * economic_part[i] + (1 - b) * energy_part[i])**(theta - 1)

                if self.damage_to_productivity == True:
                    dnet_output[i, j] = (
                        1 - damefrac_i) / (1 - self.frac_damage_prod * damefrac_i) * dgross_output[i, j]
                else:
                    dnet_output[i, j] = (1 - damefrac_i) * dgross_output[i, j]

                if i == j:
                    denergy_investment[i, j] = net_output + \
                        self.share_energy_investment[years[i]
                                                     ] * dnet_output[i, j]

                    # Saturation of renewable invest at n * invest wo tax with
                    # n -> co2_invest_limit entry parameter
                    if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:
                        # Base function:
                        # ren_investments = self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0 * \
                        #    (9.0 + np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments))
                        # Derivative:
                        #dren_investments = d(self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output * 9 / 10.0)
                        #  + d(self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10.0
                        #  * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments))
                        # So d(u*v*w) = u'.v.w + u.v'.w + u.v.w' with:
                        #  u = self.co2_invest_limit * self.share_energy_investment[years[i]]
                        #  v = net_output / 10.0
                        #  w = np.exp(- self.co2_invest_limit * self.share_energy_investment[year] * net_output / ren_investments)
                        # With w'= d(- self.co2_invest_limit *
                        # self.share_energy_investment[year] * net_output /
                        # ren_investments) * np.exp(- self.co2_invest_limit *
                        # energy_investment_wo_tax / ren_investments)
                        denergy_investment[i, j] += (self.co2_invest_limit * net_output + self.co2_invest_limit * dnet_output[i, j] * self.share_energy_investment[years[i]]) * 9 / 10 \
                            + self.co2_invest_limit * net_output / 10 * np.exp(- self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] / 10 * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (- self.co2_invest_limit * net_output - self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j]) / ren_investments \
                            * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments)

                else:
                    # Same methodology but
                    # self.share_energy_investment[years[i]] is identity matrix
                    # so u' = 0
                    if ren_investments > self.co2_invest_limit * energy_investment_wo_tax:

                        denergy_investment[i, j] = self.share_energy_investment[years[i]] * dnet_output[i, j] + \
                            self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] * 9 / 10 \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j] / 10 * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments) \
                            + self.co2_invest_limit * self.share_energy_investment[years[i]] * net_output / 10 * (- self.co2_invest_limit * self.share_energy_investment[years[i]] * dnet_output[i, j]) / ren_investments \
                            * np.exp(- self.co2_invest_limit * energy_investment_wo_tax / ren_investments)
                    else:
                        denergy_investment[i, j] = self.share_energy_investment[years[i]
                                                                                ] * dnet_output[i, j]

                if i == j:
                    dinvestment[i, j] = denergy_investment[i, j] + \
                        self.share_n_energy_investment[years[i]
                                                       ] * dnet_output[i, j] - net_output
                else:
                    dinvestment[i, j] = denergy_investment[i, j] + \
                        self.share_n_energy_investment[years[i]
                                                       ] * dnet_output[i, j]

                if i < nb_years - 1:
                    capital_after = self.economics_df.at[years[i + 1], 'capital']
                    if capital_after == self.lo_capital:
                        dcapital[i + 1, j] = 0
                    else:
                        dcapital[i + 1, j] = dcapital[i, j] * (
                            1 - self.depreciation_capital) ** self.time_step + self.time_step * dinvestment[i, j]

        return dgross_output, dinvestment, denergy_investment, dnet_output 

    """-------------------END of Gradient functions-------------------"""

 