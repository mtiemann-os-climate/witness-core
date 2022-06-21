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
from climateeconomics.core.core_witness.tempchange_model_v2 import TempChange
from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, TwoAxesInstanciatedChart
from sos_trades_core.tools.post_processing.charts.chart_filter import ChartFilter
from copy import deepcopy
import pandas as pd
import numpy as np


class TempChangeDiscipline(ClimateEcoDiscipline):
    "     Temperature evolution"

    # ontology information
    _ontology_data = {
        'label': 'Temperature Change WITNESS Model',
        'type': 'Research',
        'source': 'SoSTrades Project',
        'validated': '',
        'validated_by': 'SoSTrades Project',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': 'fas fa-thermometer-three-quarters fa-fw',
        'version': '',
    }
    years = np.arange(2020, 2101)
    DESC_IN = {
        'year_start': ClimateEcoDiscipline.YEAR_START_DESC_IN,
        'year_end': ClimateEcoDiscipline.YEAR_END_DESC_IN,
        'time_step': ClimateEcoDiscipline.TIMESTEP_DESC_IN,
        'init_temp_ocean': {'type': 'float', 'default': 0.02794825, 'user_level': 2, 'unit': '°C'},
        'init_temp_atmo': {'type': 'float', 'default': 1.05, 'user_level': 2, 'unit': '°C'},
        'eq_temp_impact': {'type': 'float', 'unit': '-', 'default': 3.1, 'user_level': 3},
        'forcing_model': {'type': 'string', 'default': 'Meinshausen', 'possible_values': ['DICE', 'Myhre', 'Etminan', 'Meinshausen'], 'structuring': True},
        'climate_upper': {'type': 'float', 'default': 0.1005, 'user_level': 3, 'unit': '-'},
        'transfer_upper': {'type': 'float', 'default': 0.088, 'user_level': 3, 'unit': '-'},
        'transfer_lower': {'type': 'float', 'default': 0.025, 'user_level': 3, 'unit': '-'},
        'forcing_eq_co2': {'type': 'float', 'default': 3.74, 'user_level': 3, 'unit': '-'},
        'pre_indus_co2_concentration_ppm': {'type': 'float', 'default': 278., 'unit': 'ppm', 'user_level': 3},
        'lo_tocean': {'type': 'float', 'default': -1.0, 'user_level': 3, 'unit': '°C'},
        'up_tatmo': {'type': 'float', 'default': 12.0, 'user_level': 3, 'unit': '°C'},
        'up_tocean': {'type': 'float', 'default': 20.0, 'user_level': 3, 'unit': '°C'},
        'ghg_cycle_df': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness'},
        'alpha': ClimateEcoDiscipline.ALPHA_DESC_IN,
        'beta': {'type': 'float', 'range': [0., 1.], 'default': 0.5, 'unit': '-',
                 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'temperature_obj_option': {'type': 'string',
                                   'possible_values': [TempChange.LAST_TEMPERATURE_OBJECTIVE,
                                                       TempChange.INTEGRAL_OBJECTIVE],
                                   'default': TempChange.INTEGRAL_OBJECTIVE,
                                   'visibility': 'Shared', 'namespace': 'ns_witness'},
        'temperature_change_ref': {'type': 'float', 'default': 0.2, 'unit': '°C', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
                                   'namespace': 'ns_ref', 'user_level': 2},

        'scale_factor_atmo_conc': {'type': 'float', 'default': 1e-2, 'unit': '-', 'user_level': 2, 'visibility': 'Shared',
                                   'namespace': 'ns_witness'},
        'temperature_end_constraint_limit': {'type': 'float', 'default': 1.5, 'unit': '°C', 'user_level': 2},
        'temperature_end_constraint_ref': {'type': 'float', 'default': 3., 'unit': '°C', 'user_level': 2},
    }

    DESC_OUT = {
        'temperature_df': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness', 'unit': '°C'},
        'temperature_detail_df': {'type': 'dataframe', 'unit': '°C'},
        'forcing_detail_df': {'type': 'dataframe', 'unit': 'W.m-2'},
        'temperature_objective': {'type': 'array', 'unit': '-', 'visibility': 'Shared', 'namespace': 'ns_witness'},
        'temperature_constraint': {'type': 'array', 'unit': '-', 'visibility': 'Shared', 'namespace': 'ns_witness'}}

    _maturity = 'Research'

    def setup_sos_disciplines(self):
        dynamic_inputs = {}

        if 'forcing_model' in self._data_in:
            forcing_model = self.get_sosdisc_inputs('forcing_model')
            if forcing_model == 'DICE':

                dynamic_inputs['init_forcing_nonco'] = {
                    'type': 'float', 'default': 0.83, 'unit': 'W.m-2', 'user_level': 2}
                dynamic_inputs['hundred_forcing_nonco'] = {
                    'type': 'float', 'default': 1.1422, 'unit': 'W.m-2', 'user_level': 2}
            else:
                # Default values for FAIR : 722 ppm and 273 ppm
                # Default values for FUND : 790 ppm and 285 ppm
                dynamic_inputs['pre_indus_ch4_concentration_ppm'] = {
                    'type': 'float', 'default': 722., 'unit': 'ppm', 'user_level': 2}
                dynamic_inputs['pre_indus_n2o_concentration_ppm'] = {
                    'type': 'float', 'default': 273., 'unit': 'ppm', 'user_level': 2}
        self.add_inputs(dynamic_inputs)

    def init_execution(self):
        in_dict = self.get_sosdisc_inputs()
        self.model = TempChange(in_dict)

    def run(self):
        ''' model execution '''
        # get inputs
        in_dict = self.get_sosdisc_inputs()
#         carboncycle_df = in_dict.pop('carboncycle_df')

        # model execution
        temperature_df, temperature_objective = self.model.compute(in_dict)

        # store output data
        out_dict = {"temperature_detail_df": temperature_df,
                    "temperature_df": temperature_df[['years', 'temp_atmo']],
                    'forcing_detail_df': self.model.forcing_df,
                    'temperature_objective': temperature_objective,
                    'temperature_constraint': self.model.temperature_end_constraint}
        self.store_sos_outputs_values(out_dict)

    def compute_sos_jacobian(self):
        """ 
        Compute jacobian for each coupling variable 
        gradient of coupling variable to compute: 
        temperature_df
          - 'forcing':
                - carboncycle_df, 'atmo_conc'
          -'temp_atmo'
                - carboncycle_df, 'atmo_conc'
          - 'temp_ocean',
                - carboncycle_df, 'atmo_conc'
        """
        d_tempatmo_d_atmoconc, d_tempocean_d_atmoconc = self.model.compute_d_temp_atmo()
        d_tempatmoobj_d_temp_atmo = self.model.compute_d_temp_atmo_objective()
        temperature_constraint_ref = self.get_sosdisc_inputs(
            'temperature_end_constraint_ref')
        self.set_partial_derivative_for_other_types(
            ('temperature_df', 'temp_atmo'),  ('ghg_cycle_df', 'co2_ppm'), d_tempatmo_d_atmoconc,)
        self.set_partial_derivative_for_other_types(
            ('temperature_constraint', ),  ('ghg_cycle_df', 'co2_ppm'), -d_tempatmo_d_atmoconc[-1] / temperature_constraint_ref,)
        for forcing_name, d_forcing_datmo_conc in self.model.d_forcing_datmo_conc_dict.items():
            self.set_partial_derivative_for_other_types(
                ('forcing_detail_df', forcing_name),  ('ghg_cycle_df', 'co2_ppm'), np.identity(len(d_forcing_datmo_conc)) * d_forcing_datmo_conc,)

        # dtao => derivative temp atmo obj
        # dac => derivative atmo conc
        # dta => derivative temp atmo
        # dtao/dac = dtao/dta * dta/dac
        self.set_partial_derivative_for_other_types(
            ('temperature_objective', ),  ('ghg_cycle_df', 'co2_ppm'),  d_tempatmoobj_d_temp_atmo.dot(d_tempatmo_d_atmoconc),)

    def get_chart_filter_list(self):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        chart_filters = []

        chart_list = ['temperature evolution', 'Radiative forcing']
        # First filter to deal with the view : program or actor
        chart_filters.append(ChartFilter(
            'Charts', chart_list, chart_list, 'charts'))

        return chart_filters

    def get_post_processing_list(self, chart_filters=None):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        instanciated_charts = []

        # Overload default value with chart filter
        if chart_filters is not None:
            for chart_filter in chart_filters:
                if chart_filter.filter_key == 'charts':
                    chart_list = chart_filter.selected_values

        if 'temperature evolution' in chart_list:

            to_plot = ['temp_atmo', 'temp_ocean']
            temperature_df = deepcopy(
                self.get_sosdisc_outputs('temperature_detail_df'))

            legend = {'temp_atmo': 'atmosphere temperature',
                      'temp_ocean': 'ocean temperature'}

            years = list(temperature_df.index)

            year_start = years[0]
            year_end = years[len(years) - 1]

            max_values = {}
            min_values = {}
            for key in to_plot:
                min_values[key], max_values[key] = self.get_greataxisrange(
                    temperature_df[to_plot])

            min_value = min(min_values.values())
            max_value = max(max_values.values())

            chart_name = 'Temperature evolution over the years'

            new_chart = TwoAxesInstanciatedChart('years', 'temperature evolution (degrees Celsius above preindustrial)',
                                                 [year_start - 5, year_end + 5], [
                                                     min_value, max_value],
                                                 chart_name)

            for key in to_plot:
                visible_line = True

                ordonate_data = list(temperature_df[key])

                new_series = InstanciatedSeries(
                    years, ordonate_data, legend[key], 'lines', visible_line)

                new_chart.series.append(new_series)

            instanciated_charts.append(new_chart)

        if 'Radiative forcing' in chart_list:

            forcing_df = self.get_sosdisc_outputs('forcing_detail_df')

            years = forcing_df['years'].values.tolist()

            chart_name = 'Gas Radiative forcing evolution over the years'

            new_chart = TwoAxesInstanciatedChart('years', 'Radiative forcing (W.m-2)',
                                                 chart_name=chart_name)

            for forcing in forcing_df.columns:
                if forcing != 'years':
                    new_series = InstanciatedSeries(
                        years, forcing_df[forcing].values.tolist(), forcing, 'lines')

                    new_chart.series.append(new_series)

            instanciated_charts.append(new_chart)
        return instanciated_charts