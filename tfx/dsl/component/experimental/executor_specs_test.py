# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for tfx.dsl.component.experimental.executor_specs."""

import tensorflow as tf

from tfx.dsl.component.experimental import executor_specs
from tfx.dsl.component.experimental import placeholders


class ExecutorSpecsTest(tf.test.TestCase):

  def setUp(self):
    super(ExecutorSpecsTest, self).setUp()
    self._text = 'text'
    self._input_value_placeholder = placeholders.InputValuePlaceholder(
        'input_artifact')
    self._input_uri_placeholder = placeholders.InputUriPlaceholder('input_uri')
    self._output_uri_placeholder = placeholders.OutputUriPlaceholder(
        'output_uri')
    self._exec_property_placeholder = placeholders.ExecPropertyPlaceholder(
        'exec_property_key')
    self._concat_placeholder = placeholders.ConcatPlaceholder([
        self._text, self._input_value_placeholder, self._input_uri_placeholder,
        self._output_uri_placeholder, self._exec_property_placeholder,
    ])
    self._text_concat_placeholder = placeholders.ConcatPlaceholder(
        [self._text, 'text1', placeholders.ConcatPlaceholder(['text2']),])

  def testEncodeTemplatedExecutorContainerSpec(self):
    specs = executor_specs.TemplatedExecutorContainerSpec(
        image='image',
        command=[
            self._text, self._input_value_placeholder,
            self._input_uri_placeholder, self._output_uri_placeholder,
            self._concat_placeholder
        ])
    encode_result = specs.encode()
    self.assertProtoEquals("""
      image: "image"
      commands {
        value {
          string_value: "text"
        }
      }
      commands {
        operator {
          index_op {
            expression {
              placeholder {
                key: "input_artifact"
              }
            }
          }
        }
      }
      commands {
        operator {
          artifact_uri_op {
            expression {
              operator {
                index_op {
                  expression {
                    placeholder {
                      key: "input_uri"
                    }
                  }
                  index: 0
                }
              }
            }
          }
        }
      }
      commands {
        operator {
          artifact_uri_op {
            expression {
              operator {
                index_op {
                  expression {
                    placeholder {
                      type: OUTPUT_ARTIFACT
                      key: "output_uri"
                    }
                  }
                  index: 0
                }
              }
            }
          }
        }
      }
      commands {
        operator {
          concat_op {
            expressions {
              value {
                string_value: "text"
              }
            }
            expressions {
              operator {
                index_op {
                  expression {
                    placeholder {
                      key: "input_artifact"
                    }
                  }
                  index: 0
                }
              }
            }
            expressions {
              operator {
                artifact_uri_op {
                  expression {
                    operator {
                      index_op {
                        expression {
                          placeholder {
                            key: "input_uri"
                          }
                        }
                        index: 0
                      }
                    }
                  }
                }
              }
            }
            expressions {
              operator {
                artifact_uri_op {
                  expression {
                    operator {
                      index_op {
                        expression {
                          placeholder {
                            type: OUTPUT_ARTIFACT
                            key: "output_uri"
                          }
                        }
                        index: 0
                      }
                    }
                  }
                }
              }
            }
            expressions {
              placeholder {
                type: EXEC_PROPERTY
                key: "exec_property_key"
              }
            }
          }
        }
      }""", encode_result)

  def testEncodeTemplatedExecutorContainerSpec_withConcatAllText(self):
    specs = executor_specs.TemplatedExecutorContainerSpec(
        image='image',
        command=[
            self._text_concat_placeholder
        ],
        args=[
            self._text_concat_placeholder
        ])
    encode_result = specs.encode()
    self.assertProtoEquals("""
      image: "image"
      commands {
        value {
          string_value: "texttext1text2"
        }
      }
      args {
        value {
          string_value: "texttext1text2"
        }
      }""", encode_result)


if __name__ == '__main__':
  tf.test.main()
