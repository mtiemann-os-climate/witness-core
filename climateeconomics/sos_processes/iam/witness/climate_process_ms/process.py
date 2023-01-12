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
from sostrades_core.sos_processes.base_process_builder import BaseProcessBuilder


class ProcessBuilder(BaseProcessBuilder):

    # ontology information
    _ontology_data = {
        'label': 'Climate Process Multiscenario Process',
        'description': '',
        'category': '',
        'version': '',
    }

    def get_builders(self):

        builder_cdf_list = self.ee.factory.get_builder_from_process(
            'climateeconomics.sos_processes.iam.witness', 'climate_process')

        scatter_scenario_name = 'Scenarios'
        # modify namespaces defined in the child process
        self.ee.ns_manager.update_namespace_list_with_extra_ns(
            scatter_scenario_name, after_name=self.ee.study_name)

        # Add new namespaces needed for the scatter multiscenario
        ns_dict = {'ns_scatter_scenario': f'{self.ee.study_name}',
                   'ns_post_processing': f'{self.ee.study_name}.Post-processing'}

        self.ee.ns_manager.add_ns_def(ns_dict)

        multi_scenario = self.ee.factory.create_driver(
            'Scenarios', builder_cdf_list, flatten_subprocess=False
        )
        """
        self.ee.post_processing_manager.add_post_processing_module_to_namespace('ns_post_processing',
                                                                                'climateeconomics.sos_wrapping.sos_wrapping_witness.post_proc_climate_ms.post_processing_climate')

        """
        return multi_scenario
