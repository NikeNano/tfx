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
"""Task scheduler interface and registry."""

import abc
import typing
from typing import Optional, Type, TypeVar

import attr
from tfx.orchestration import metadata
from tfx.orchestration.experimental.core import common_utils
from tfx.orchestration.experimental.core import status as status_lib
from tfx.orchestration.experimental.core import task as task_lib
from tfx.proto.orchestration import execution_result_pb2
from tfx.proto.orchestration import pipeline_pb2


@attr.s(auto_attribs=True, frozen=True)
class TaskSchedulerResult:
  """Response from the task scheduler.

  Attributes:
    status: Scheduler status that reflects scheduler level issues, such as task
      cancellation, failure to start the executor, etc. Executor status set in
      `executor_output` matters if the scheduler status is `OK`. Otherwise,
      `executor_output` may be `None` and is ignored.
    executor_output: An instance of `ExecutorOutput` containing the results of
      task execution.
  """
  status: status_lib.Status
  executor_output: Optional[execution_result_pb2.ExecutorOutput] = None


class TaskScheduler(abc.ABC):
  """Interface for task schedulers."""

  def __init__(self, mlmd_handle: metadata.Metadata,
               pipeline: pipeline_pb2.Pipeline, task: task_lib.Task):
    """Constructor.

    Args:
      mlmd_handle: A handle to the MLMD db.
      pipeline: The pipeline IR proto.
      task: Task to be executed.
    """
    self.mlmd_handle = mlmd_handle
    self.pipeline = pipeline
    self.task = task

  @abc.abstractmethod
  def schedule(self) -> TaskSchedulerResult:
    """Schedules task execution and returns the results of execution.

    This method blocks until task execution completes (successfully or not) or
    until explicitly cancelled by a call to `cancel`. When cancelled, `schedule`
    is expected to stop any ongoing work, clean up and return as soon as
    possible. Note that `cancel` will be invoked from a different thread than
    `schedule` and hence the concrete implementations must be thread safe. It's
    technically possible for `cancel` to be invoked before `schedule`; scheduler
    implementations should handle this case by returning from `schedule`
    immediately.
    """

  @abc.abstractmethod
  def cancel(self) -> None:
    """Cancels task scheduler.

    This method will be invoked from a different thread than the thread that's
    blocked on call to `schedule`. `cancel` must return immediately when called.
    Upon cancellation, `schedule` method is expected to stop any ongoing work,
    clean up and return as soon as possible. It's technically possible for
    `cancel` to be invoked before `schedule`; scheduler implementations should
    handle this case by returning from `schedule` immediately.
    """


T = TypeVar('T', bound='TaskSchedulerRegistry')


class TaskSchedulerRegistry:
  """A registry for task schedulers."""

  _task_scheduler_registry = {}

  @classmethod
  def register(cls: Type[T], executor_spec_type_url: str,
               scheduler_class: Type[TaskScheduler]) -> None:
    """Registers a new task scheduler for the given executor spec type url.

    Args:
      executor_spec_type_url: The URL of the executor spec type.
      scheduler_class: The class that will be instantiated for a matching task.

    Raises:
      ValueError: If `executor_spec_type_url` is already in the registry.
    """
    if executor_spec_type_url in cls._task_scheduler_registry:
      raise ValueError(
          'A task scheduler already exists for the executor spec type url: {}'
          .format(executor_spec_type_url))
    cls._task_scheduler_registry[executor_spec_type_url] = scheduler_class

  @classmethod
  def clear(cls: Type[T]) -> None:
    cls._task_scheduler_registry.clear()

  @classmethod
  def create_task_scheduler(cls: Type[T], mlmd_handle: metadata.Metadata,
                            pipeline: pipeline_pb2.Pipeline,
                            task: task_lib.Task) -> TaskScheduler:
    """Creates a task scheduler for the given task.

    Note that this assumes deployment_config packed in the pipeline IR is of
    type `IntermediateDeploymentConfig`. This detail may change in the future.

    Args:
      mlmd_handle: A handle to the MLMD db.
      pipeline: The pipeline IR.
      task: The task that needs to be scheduled.

    Returns:
      An instance of `TaskScheduler` for the given task.

    Raises:
      NotImplementedError: Raised if not an `ExecNodeTask`.
      ValueError: Deployment config not present in the IR proto or if executor
        spec for the node corresponding to `task` not configured in the IR.
    """
    if not task_lib.is_exec_node_task(task):
      raise NotImplementedError(
          'Can create a task scheduler only for an `ExecNodeTask`.')
    task = typing.cast(task_lib.ExecNodeTask, task)
    executor_spec = common_utils.get_executor_spec(pipeline,
                                                   task.node_uid.node_id)
    if executor_spec is None:
      raise ValueError(
          f'Executor spec for node id `{task.node_uid.node_id}` not found in '
          f'pipeline IR.')
    executor_spec_type_url = executor_spec.type_url
    return cls._task_scheduler_registry[executor_spec_type_url](
        mlmd_handle=mlmd_handle, pipeline=pipeline, task=task)
