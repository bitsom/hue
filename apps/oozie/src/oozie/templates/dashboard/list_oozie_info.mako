## Licensed to Cloudera, Inc. under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  Cloudera, Inc. licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

<%!
  from desktop.views import commonheader, commonfooter
  from django.utils.translation import ugettext as _
%>

<%namespace name="layout" file="../navigation-bar.mako" />
<%namespace name="utils" file="../utils.inc.mako" />

${ commonheader(_("Oozie Information"), "oozie", user) | n,unicode }
${ layout.menubar(section='oozie', dashboard=True) }


<div class="container-fluid">

  <div class="card card-small">
  <div class="card-body">
  <p>

  <h1 class="card-heading card-heading-noborder simple pull-right" style="margin-top: -4px;">
  ${ _('Oozie status') }
  <div class="label ${ utils.get_status(oozie_status['systemMode']) }" style="line-height: 20px; vertical-align: middle">
    ${ oozie_status['systemMode'] }
  </div>
  </h1>

  <ul class="nav nav-tabs">
    % if instrumentation:
    <li class="active"><a href="#instrumentation" data-toggle="tab">${ _('Instrumentation') }</a></li>
    % else:
    <li class="active"><a href="#metrics" data-toggle="tab">${ _('Metrics') }</a></li>
    % endif
    <li><a href="#configuration" data-toggle="tab">${ _('Configuration') }</a></li>
  </ul>

  <div class="tab-content" style="padding-bottom:200px">

    % if instrumentation:
    <div class="tab-pane active" id="instrumentation">
      <form class="form-search">
        <input type="text" class="searchFilter input-xlarge search-query" placeholder="${_('Text Filter')}">
      </form>
      <div class="tabbable">
        <ul class="nav nav-pills">
            % for category in instrumentation.iterkeys():
            <li
            % if loop.first:
              class="active"
            % endif
            >
              <a href="#${ category }" data-toggle="tab">${ category }</a>
            </li>
            % endfor
        </ul>

        <div class="tab-content">
            % for category in instrumentation.iterkeys():
            <div class="tab-pane
              % if loop.first:
              active
              % endif
            " id="${ category }">

              % for index, group in enumerate(instrumentation[category]):
                <p class="nav-header">${ group['group'] }</p>
              <table id="intrumentationTable-${ category }-${ index }" class="table table-striped table-condensed">
                <thead>
                <th></th>
                <th></th>
                </thead>
              <tbody>
                % for item in group['data']:
                <tr>
                <% name = item.pop('name') %>
                  <td>${ name }</td>
                % if category == 'timers':
                  <td>
                    % for label, timer in zip(['ownMinTime', 'ownTimeStdVar', 'totalTimeStdVar', 'ownTimeAvg', 'ticks', 'name', 'ownMaxTime', 'totalMinTime', 'totalMaxTime', 'totalTimeAvg'], item.values()):
                    ${ label } :
                    % if label == 'name':
                      ${ name } -
                    % endif
                    ${ timer }
                    % if not loop.last:
                        </br>
                    % endif
                    % endfor
                  </td>
                % else:
                    <td>${ ', '.join(map(str, item.values())) }</td>
                % endif
                </tr>
                % endfor
              </tbody>
              </table>
              % endfor
            </div>
            % endfor
        </div>
      </div>
    </div>
    % endif

    % if metrics:
    <div class="tab-pane active" id="metrics">
      <form class="form-search">
        <input type="text" class="searchFilter input-xlarge search-query" placeholder="${_('Text Filter')}">
      </form>
      ${ metrics }
    </div>
    % endif

    <div class="tab-pane" id="configuration">
      <form class="form-search">
        <input type="text" class="searchFilter input-xlarge search-query" placeholder="${_('Text Filter')}">
      </form>
      ${ utils.display_conf(configuration, "configurationTable") }
    </div>


    <div style="margin-bottom: 16px">
      <a href="${ url('oozie:list_oozie_bundles') }" class="btn">${ _('Back') }</a>
    </div>

    </p>
    </div>
    </div>
  </div>


<script>
  $(document).ready(function(){
    $("a[data-row-selector='true']").jHueRowSelector();

    $("*[rel=tooltip]").tooltip();

    var _metadataTable = $("#configurationTable").dataTable({
        "bPaginate": false,
        "bLengthChange": false,
        "bInfo": false,
        "bAutoWidth": false,
        "aoColumns": [
            { "sWidth": "30%" },
            { "sWidth": "70%" }
        ],
        "oLanguage": {
           "sEmptyTable": "${_('No data available')}",
           "sZeroRecords": "${_('No matching records')}",
        }
   });

   var instrumentationTables = [];

   % for category in instrumentation.iterkeys():
      % for index in range(len(instrumentation[category])):
        var table = $("#intrumentationTable-${ category }-${ index }").dataTable({
            "bPaginate": false,
            "bLengthChange": false,
            "bInfo": false,
            "bAutoWidth": false,
            "aoColumns": [
                { "sWidth": "30%" },
                { "sWidth": "70%" }
            ],
            "oLanguage": {
                "sEmptyTable": "${_('No data available')}",
                "sZeroRecords": "${_('No matching records')}"
            }
        });
        $("#intrumentationTable-${ category }-${ index } th").removeClass();
        instrumentationTables.push(table);
      % endfor
    % endfor


    $(".searchFilter").keyup(function(){
        _metadataTable.fnFilter($(this).val());
        $.each(instrumentationTables, function(index, item){
          item.fnFilter($(".searchFilter").val());
        });
    });

    $(".dataTables_wrapper").css("min-height","0");
    $(".dataTables_filter").hide();
  });
</script>

${ commonfooter(messages) | n,unicode }
