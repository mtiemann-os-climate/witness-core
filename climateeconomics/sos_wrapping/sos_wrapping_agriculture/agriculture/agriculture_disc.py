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
from climateeconomics.core.core_witness.climateeco_discipline import ClimateEcoDiscipline
from climateeconomics.core.core_agriculture.agriculture import Agriculture,\
    OrderOfMagnitude
from sos_trades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries,\
    TwoAxesInstanciatedChart
import numpy as np
import pandas as pd


class AgricultureDiscipline(ClimateEcoDiscipline):
    ''' Disscipline intended to host agricluture model
    '''
    default_year_start = 2020
    default_year_end = 2050
    default_years = np.arange(default_year_start, default_year_end + 1, 1)
    default_kg_to_m2 = {'red meat': 348,
                        'white meat': 14.5,
                        'milk': 8.9,
                        'eggs': 6.3,
                        'rice and maize': 2.9,
                        'potatoes': 0.9,
                        'fruits and vegetables': 0.8,
                        }
    default_kg_to_kcal = {'red meat': 2566,
                          'white meat': 1860,
                          'milk': 550,
                          'eggs': 1500,
                          'rice and maize': 1150,
                          'potatoes': 670,
                          'fruits and vegetables': 624,
                          }
    year_range = default_year_end - default_year_start + 1
    default_red_to_white_meat = np.linspace(0, 50, year_range)
    default_meat_to_vegetables = np.linspace(0, 25, year_range)

    DESC_IN = {'year_start': {'type': 'int', 'default': default_year_start, 'unit': '[-]', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_public'},
               'year_end': {'type': 'int', 'default': default_year_end, 'unit': '[-]', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_public'},
               'time_step': {'type': 'int', 'default': 1, 'visibility': 'Shared', 'namespace': 'ns_witness', 'user_level': 2},
               'population_df': {'type': 'dataframe', 'unit': 'millions of people',
                                 'dataframe_descriptor': {'years': ('float', None, False),
                                                          'population': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False,
                                 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
               'diet_df': {'type': 'dataframe', 'unit': 'kg_food/person/year',
                           'dataframe_descriptor': {'years': ('float', None, False),
                                                    'red meat': ('float', [0, 1e9], True), 'white meat': ('float', [0, 1e9], True), 'milkt': ('float', [0, 1e9], True),
                                                    'eggs': ('float', [0, 1e9], True), 'rice and maize': ('float', [0, 1e9], True), 'potatoes': ('float', [0, 1e9], True),
                                                    'fruits and vegetables': ('float', [0, 1e9], True)},
                           'dataframe_edition_locked': False, 'namespace': 'ns_agriculture'},
               'kg_to_kcal_dict': {'type': 'dict', 'default': default_kg_to_kcal, 'unit': 'kcal/kg', 'namespace': 'ns_agriculture'},
               'kg_to_m2_dict': {'type': 'dict', 'default': default_kg_to_m2, 'unit': 'm^2/kg',  'namespace': 'ns_agriculture'},
               'red_to_white_meat': {'type': 'array', 'default': default_red_to_white_meat, 'unit': '%', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_agriculture'},
               'meat_to_vegetables': {'type': 'array', 'default': default_meat_to_vegetables, 'unit': '%', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_agriculture'},
               'other_use_agriculture': {'type': 'array', 'unit': 'ha/person', 'namespace': 'ns_agriculture'},
               'temperature_df': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness'},
               'param_a': {'type': 'float', 'default': - 0.00833, 'user_level': 3},
               'param_b': {'type': 'float', 'default': - 0.04167, 'user_level': 3}
               }

    DESC_OUT = {
        'total_food_land_surface': {
            'type': 'dataframe', 'unit': 'Gha', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'food_land_surface_df': {
            'type': 'dataframe', 'unit': 'Gha'},
        'food_land_surface_percentage_df': {'type': 'dataframe', 'unit': '%'},
        'updated_diet_df': {'type': 'dataframe', 'unit': 'kg/person/year'},
        'agriculture_productivity_evolution': {'type': 'dataframe'}
        #'percentage_diet_df': {'type': 'dataframe', 'unit': '%'},
    }

    AGRICULTURE_CHARTS = 'agriculture and diet charts'

    def init_execution(self):
        inputs = list(self.DESC_IN.keys())
        param = self.get_sosdisc_inputs(inputs, in_dict=True)

        self.agriculture_model = Agriculture(param)

    def run(self):

        #-- get inputs
        inputs = list(self.DESC_IN.keys())
        inp_dict = self.get_sosdisc_inputs(inputs, in_dict=True)
        self.agriculture_model.red_to_white_meat = inp_dict[Agriculture.RED_TO_WHITE_MEAT]
        self.agriculture_model.meat_to_vegetables = inp_dict[Agriculture.MEAT_TO_VEGETABLES]
        #-- compute
        population_df = inp_dict.pop('population_df')
        temperature_df = inp_dict['temperature_df']
        self.agriculture_model.compute(population_df, temperature_df)

        #years = np.arange(inp_dict['year_start'], inp_dict['year_end'] + 1)

        outputs_dict = {
            'food_land_surface_df': self.agriculture_model.food_land_surface_df,
            'total_food_land_surface': self.agriculture_model.total_food_land_surface,
            'food_land_surface_percentage_df': self.agriculture_model.food_land_surface_percentage_df,
            'updated_diet_df': self.agriculture_model.updated_diet_df,
            'agriculture_productivity_evolution': self.agriculture_model.productivity_evolution,
            #'percentage_diet_df': self.agriculture_model.percentage_diet_df,
        }

        #-- store outputs
        self.store_sos_outputs_values(outputs_dict)

    def compute_sos_jacobian(self):
        """
        Compute jacobian for each coupling variable
        """
        inputs_dict = self.get_sosdisc_inputs()
        population_df = inputs_dict.pop('population_df')
        temperature_df = inputs_dict['temperature_df']
        model = self.agriculture_model
        model.compute(population_df, temperature_df)

        # get variable
        food_land_surface_df = model.food_land_surface_df

        # get column of interest
        food_land_surface_df_columns = list(food_land_surface_df)
        food_land_surface_df_columns.remove('years')
        food_land_surface_df_columns.remove('total surface (Gha)')

        # sum is needed to have d_total_surface_d_population
        summ = np.identity(len(food_land_surface_df.index)) * 0
        for column_name in food_land_surface_df_columns:
            if column_name == 'other (Gha)':
                result = model.d_other_surface_d_population()
            else:
                result = model.d_land_surface_d_population(column_name)
            summ += result

        self.set_partial_derivative_for_other_types(
            ('total_food_land_surface', 'total surface (Gha)'), ('population_df', 'population'), summ,)
        d_total_d_temperature = model.d_food_land_surface_d_temperature(
            temperature_df, 'total surface (Gha)')
        self.set_partial_derivative_for_other_types(
            ('total_food_land_surface', 'total surface (Gha)'), ('temperature_df', 'temp_atmo'), d_total_d_temperature,)

    def get_chart_filter_list(self):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        chart_filters = []

        chart_list = [
            AgricultureDiscipline.AGRICULTURE_CHARTS, 'Agriculture Productivity Evolution']

        # First filter to deal with the view : program or actor
        chart_filters.append(ChartFilter(
            'Charts filter', chart_list, chart_list, 'charts'))

        return chart_filters

    def get_post_processing_list(self, chart_filters=None):
        '''
        For the outputs, making a graph for tco vs year for each range and for specific
        value of ToT with a shift of five year between then
        '''
        instanciated_charts = []

        # Overload default value with chart filter
        if chart_filters is not None:
            for chart_filter in chart_filters:
                if chart_filter.filter_key == 'charts':
                    chart_list = chart_filter.selected_values

        if AgricultureDiscipline.AGRICULTURE_CHARTS in chart_list:

            surface_df = self.get_sosdisc_outputs('food_land_surface_df')
            years = surface_df['years'].values.tolist()

            agriculture_surfaces = surface_df['total surface (Gha)'].values
            agriculture_surface_series = InstanciatedSeries(
                years, agriculture_surfaces.tolist(), 'Total agriculture surface', InstanciatedSeries.LINES_DISPLAY)

            series_to_add = []

            for key in surface_df.keys():

                if key == 'years':
                    pass
                elif key.startswith('total'):
                    pass
                else:

                    new_series = InstanciatedSeries(
                        years, (surface_df[key]).values.tolist(), key, InstanciatedSeries.BAR_DISPLAY)

                    series_to_add.append(new_series)

            new_chart = TwoAxesInstanciatedChart('years', 'surface (Gha)',
                                                 chart_name='Surface taken to produce food over time', stacked_bar=True)
            new_chart.add_series(agriculture_surface_series)

            for serie in series_to_add:
                new_chart.add_series(serie)

            instanciated_charts.append(new_chart)

            # chart of land surface in %
            surface_percentage_df = self.get_sosdisc_outputs(
                'food_land_surface_percentage_df')

            series_to_add = []
            for key in surface_percentage_df.keys():

                if key == 'years':
                    pass
                elif key.startswith('total'):
                    pass
                else:

                    new_series = InstanciatedSeries(
                        years, surface_percentage_df[key].values.tolist(), key, InstanciatedSeries.BAR_DISPLAY)

                    series_to_add.append(new_series)

            new_chart = TwoAxesInstanciatedChart('years', 'surface (%)',
                                                 chart_name='Share of the surface used to produce food over time', stacked_bar=True)
            # add a fake serie of value before the other serie to keep the same color than in the first graph,
            # where the line plot of total surface take the first color
            fake_serie = InstanciatedSeries(
                years, surface_percentage_df[key].values.tolist() * 0, '', InstanciatedSeries.BAR_DISPLAY)

            new_chart.add_series(fake_serie)

            for serie in series_to_add:
                new_chart.add_series(serie)

            instanciated_charts.append(new_chart)

            # chart of the updated diet
            updated_diet_df = self.get_sosdisc_outputs(
                'updated_diet_df')

            series_to_add = []
            for key in updated_diet_df.keys():

                if key == 'years':
                    pass
                elif key.startswith('total'):
                    pass
                else:

                    new_series = InstanciatedSeries(
                        years, updated_diet_df[key].values.tolist(), key, InstanciatedSeries.BAR_DISPLAY)

                    series_to_add.append(new_series)

            new_chart = TwoAxesInstanciatedChart('years', 'food quantity (kg / person / year)',
                                                 chart_name='Evolution of the diet over time', stacked_bar=True)

            # add a fake serie of value before the other serie to keep the same color than in the first graph,
            # where the line plot of total surface take the first color
            fake_serie = InstanciatedSeries(
                years, surface_percentage_df[key].values.tolist() * 0, '', InstanciatedSeries.BAR_DISPLAY)

            new_chart.add_series(fake_serie)

            for serie in series_to_add:
                new_chart.add_series(serie)

            instanciated_charts.append(new_chart)

        if 'Agriculture Productivity Evolution' in chart_list:

            prod_df = self.get_sosdisc_outputs(
                'agriculture_productivity_evolution')
            years = list(prod_df.index)

            chart_name = 'Agriculture productivity evolution'

            new_chart = TwoAxesInstanciatedChart('years', ' productivity evolution (%)',
                                                 chart_name=chart_name)

            visible_line = True
            ordonate_data = list(prod_df['productivity_evolution'] * 100)

            new_series = InstanciatedSeries(
                years, ordonate_data, 'productivity_evolution', 'lines', visible_line)

            new_chart.series.append(new_series)
            instanciated_charts.append(new_chart)

        return instanciated_charts
