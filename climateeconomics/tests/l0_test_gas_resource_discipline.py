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
'''
mode: python; py-indent-offset: 4; tab-width: 8; coding: utf-8
'''
import unittest
from os.path import join, dirname
from pandas import read_csv
from climateeconomics.core.core_resources.resources_model import ResourceModel
from sos_trades_core.execution_engine.execution_engine import ExecutionEngine

class GasModelTestCase(unittest.TestCase):

    def setUp(self):
        '''
        Initialize third data needed for testing
        '''
        self.year_start = 2020
        self.year_end = 2055
        self.production_start=2010

        data_dir = join(dirname(__file__), 'data')

        self.energy_gas_demand_df = read_csv(
            join(data_dir, 'all_demand_from_energy_mix.csv'))
        # part to adapt lenght to the year range

        self.energy_gas_demand_df = self.energy_gas_demand_df.loc[self.energy_gas_demand_df['years']
                                                                    >= self.year_start]
        self.energy_gas_demand_df= self.energy_gas_demand_df.loc[self.energy_gas_demand_df['years']
                                                                  <= self.year_end]

        self.param = {'All_Demand': self.energy_gas_demand_df,
                      'year_start': self.year_start,
                      'year_end': self.year_end,
                      'production_start': self.production_start
                      }

    def test_Gas_model(self):
        '''
        Basique test of land use model
        Mainly check the overal run without value checks (will be done in another test)
        '''
        Gas_use = ResourceModel(self.param)
        Gas_use.compute(self.energy_gas_demand_df,'natural_gas_resource',2010)

    def test_gas_discipline(self):
        ''' 
        Check discipline setup and run
        '''
        name = 'Test'
        model_name = 'all_resource.gas_resource'
        ee = ExecutionEngine(name)
        ns_dict = {'ns_public': f'{name}',
                   'ns_witness': f'{name}.{model_name}',
                   'ns_functions': f'{name}.{model_name}',
                   'natural_gas_resource': f'{name}.{model_name}',
                   'ns_resource': f'{name}.{model_name}'
                   }
        ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_resources.sos_wrapping_gas_resource.gas_resource_model.gas_resource_disc.GasDiscipline'
        builder = ee.factory.get_builder_from_module(model_name, mod_path)

        ee.factory.set_builders_to_coupling_builder(builder)

        ee.configure()
        ee.display_treeview_nodes()

        inputs_dict = {f'{name}.year_start': self.year_start,
                       f'{name}.year_end': self.year_end,
                       f'{name}.{model_name}.{ResourceModel.DEMAND}': self.energy_gas_demand_df,
                       'production_start': self.production_start
                       }
        ee.load_study_from_input_dict(inputs_dict)

        ee.execute()

        disc = ee.dm.get_disciplines_with_name(
            f'{name}.{model_name}')[0]
        filter = disc.get_chart_filter_list()
        graph_list = disc.get_post_processing_list(filter)
#        for graph in graph_list:
#            graph.to_plotly().show()
